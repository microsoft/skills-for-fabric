using System.Diagnostics;
using System.IO.Compression;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Xml;
using Microsoft.SqlServer.Dac.Model;

try
{
if (args.Length is < 2 or > 3 || (args.Length == 3 && args[2] != "--allow-trusted-project-build"))
{
    Console.Error.WriteLine("Usage: DedicatedPoolTool <input.dacpac|project.zip> <output-directory> [--allow-trusted-project-build]");
    return 2;
}

var inputPath = Path.GetFullPath(args[0]);
var outputPath = Path.GetFullPath(args[1]);
var allowTrustedProjectBuild = args.Length == 3;
if (!File.Exists(inputPath))
{
    Console.Error.WriteLine($"Input does not exist: {inputPath}");
    return 2;
}

Directory.CreateDirectory(outputPath);
var temporaryRoot = Path.Combine(Path.GetTempPath(), $"synapse-migration-{Guid.NewGuid():N}");
Directory.CreateDirectory(temporaryRoot);

try
{
    var dacpacPath = ResolveDacpac(inputPath, temporaryRoot, allowTrustedProjectBuild);
    var warnings = new BoundedBlindSpotCollection();
    (TSqlModel Model, string SelectedMode, string[] Attempts) modelLoad;
    try
    {
        modelLoad = LoadModelWithFallback(dacpacPath, warnings);
    }
    catch (ModelLoadFailureException exception)
    {
        var failureInventory = new
        {
            schemaVersion = 1,
            input = new
            {
                path = Path.GetFileName(inputPath),
                kind = Path.GetExtension(inputPath).Equals(".dacpac", StringComparison.OrdinalIgnoreCase)
                    ? "Dacpac"
                    : "ZippedSqlProject",
                resolvedDacpac = Path.GetFileName(dacpacPath)
            },
            modelLoadOptions = new
            {
                loadAsScriptBackedModel = true,
                preferredMode = "ScriptBacked",
                selectedMode = (string?)null,
                attempts = exception.Attempts,
                queryScope = "UserDefined"
            },
            status = "Blocked",
            blindSpots = warnings.ToArray()
        };
        File.WriteAllText(
            Path.Combine(outputPath, "schema-inventory.json"),
            JsonSerializer.Serialize(failureInventory, new JsonSerializerOptions { WriteIndented = true }));
        throw;
    }
    using var model = modelLoad.Model;
    var identifierComparer = model.CollationComparer;
    var modelMetadata = ExtractModelMetadata(dacpacPath);
    var conversionObjects = new List<object>();
    var evidenceObjects = new List<object>();
    var supportingObjects = new List<object>();
    Directory.CreateDirectory(Path.Combine(outputPath, "source"));

    foreach (var sourceObject in model.GetObjects(DacQueryScopes.UserDefined))
    {
        var objectType = sourceObject.ObjectType.Name ?? "Unclassified";
        var stableId = GetStableId(sourceObject);
        var category = Classify(objectType);

        if (category == ObjectCategory.Supporting)
        {
            supportingObjects.Add(CreateRecord(sourceObject, stableId, objectType, null, null, warnings, identifierComparer));
            continue;
        }

        string? sourceText = null;
        string? scriptError = null;
        try
        {
            sourceText = sourceObject.GetScript();
        }
        catch (Exception exception) when (exception is DacModelException or InvalidOperationException or NotSupportedException)
        {
            scriptError = SanitizeMessage(exception.Message);
            warnings.Add(new
            {
                code = "NonScriptableObject",
                sourceStableId = stableId,
                objectType,
                message = SanitizeMessage(exception.Message)
            });
        }
        if (scriptError is null && string.IsNullOrWhiteSpace(sourceText))
        {
            scriptError = "DacFx returned an empty object script.";
            warnings.Add(new
            {
                code = "NonScriptableObject",
                sourceStableId = stableId,
                objectType,
                message = scriptError
            });
        }

        string? sourcePath = null;
        if (!string.IsNullOrWhiteSpace(sourceText))
        {
            sourcePath = Path.Combine("source", $"{ToEvidenceFileName(stableId)}.sql").Replace('\\', '/');
            File.WriteAllText(Path.Combine(outputPath, sourcePath), sourceText);
        }

        var record = CreateRecord(sourceObject, stableId, objectType, sourcePath, scriptError, warnings, identifierComparer);
        if (category == ObjectCategory.Conversion)
        {
            record["conversionStatus"] = (bool)record["scriptable"]!
                ? "Eligible"
                : "ManualReviewRequired";
            record["sourceContractBlockers"] = Array.Empty<object>();
            conversionObjects.Add(record);
        }
        else
        {
            evidenceObjects.Add(record);
        }
    }

    var sourceContracts = ExtractSourceContracts(model, warnings, identifierComparer);
    ApplySourceContractBlockers(conversionObjects, sourceContracts, identifierComparer);
    var inventory = new
    {
        schemaVersion = 1,
        input = new
        {
            path = Path.GetFileName(inputPath),
            kind = Path.GetExtension(inputPath).Equals(".dacpac", StringComparison.OrdinalIgnoreCase)
                ? "Dacpac"
                : "ZippedSqlProject",
            resolvedDacpac = Path.GetFileName(dacpacPath)
        },
        modelLoadOptions = new
        {
            loadAsScriptBackedModel = string.Equals(
                modelLoad.SelectedMode,
                "ScriptBacked",
                StringComparison.Ordinal),
            preferredMode = "ScriptBacked",
            selectedMode = modelLoad.SelectedMode,
            attempts = modelLoad.Attempts,
            queryScope = "UserDefined"
        },
        modelMetadata,
        objects = conversionObjects,
        evidenceObjects,
        supportingObjects,
        sourceContracts,
        blindSpots = warnings.ToArray()
    };

    var jsonOptions = new JsonSerializerOptions { WriteIndented = true };
    File.WriteAllText(
        Path.Combine(outputPath, "schema-inventory.json"),
        JsonSerializer.Serialize(inventory, jsonOptions));
    Console.WriteLine(Path.Combine(outputPath, "schema-inventory.json"));
    return 0;
}
finally
{
    if (Directory.Exists(temporaryRoot))
    {
        TryDeleteDirectory(temporaryRoot);
    }
}
}
catch (Exception exception)
{
    Console.Error.WriteLine($"Dedicated Pool discovery failed: {SanitizeMessage(exception.Message)}");
    return 1;
}

static (TSqlModel Model, string SelectedMode, string[] Attempts) LoadModelWithFallback(
    string dacpacPath,
    BoundedBlindSpotCollection blindSpots)
{
    var attempts = new List<string> { "ScriptBacked" };
    try
    {
        return (
            TSqlModel.LoadFromDacpac(
                dacpacPath,
                new ModelLoadOptions { LoadAsScriptBackedModel = true }),
            "ScriptBacked",
            attempts.ToArray());
    }
    catch (Exception exception) when (
        exception is DacModelException or InvalidOperationException or NotSupportedException)
    {
        blindSpots.Add(new
        {
            code = "ScriptBackedModelLoadFailed",
            message = SanitizeMessage(exception.Message),
            fallbackMode = "ModelOnly",
            impact = "Object scripts can be unavailable in fallback mode; every missing script is recorded as NonScriptableObject."
        });
    }

    attempts.Add("ModelOnly");
    try
    {
        return (
            TSqlModel.LoadFromDacpac(
                dacpacPath,
                new ModelLoadOptions { LoadAsScriptBackedModel = false }),
            "ModelOnly",
            attempts.ToArray());
    }
    catch (Exception exception)
    {
        blindSpots.Add(new
        {
            code = "ModelOnlyModelLoadFailed",
            message = SanitizeMessage(exception.Message),
            impact = "Discovery could not load the DACPAC in either supported mode."
        });
        throw new ModelLoadFailureException(attempts.ToArray(), exception);
    }
}

static string SanitizeMessage(string message)
{
    return DedicatedPoolMessageSanitizer.Sanitize(message);
}

static void TryDeleteDirectory(string path)
{
    try
    {
        Directory.Delete(path, recursive: true);
    }
    catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
    {
        Console.Error.WriteLine($"Warning: temporary directory cleanup failed: {SanitizeMessage(exception.Message)}");
    }
}

static object ExtractModelMetadata(string dacpacPath)
{
    const int maximumTrackedTypes = 100;
    using var archive = ZipFile.OpenRead(dacpacPath);
    var modelEntry = archive.Entries.SingleOrDefault(entry =>
        entry.FullName.Equals("model.xml", StringComparison.OrdinalIgnoreCase))
        ?? throw new InvalidOperationException("The DACPAC does not contain model.xml.");
    using var stream = modelEntry.Open();
    using var reader = XmlReader.Create(stream, new XmlReaderSettings
    {
        DtdProcessing = DtdProcessing.Prohibit,
        XmlResolver = null
    });

    var elementCount = 0L;
    var untrackedTypeElementCount = 0L;
    var typeCounts = new Dictionary<string, long>(StringComparer.Ordinal);
    while (reader.Read())
    {
        if (reader.NodeType != XmlNodeType.Element || reader.LocalName != "Element")
        {
            continue;
        }

        elementCount++;
        var type = reader.GetAttribute("Type") ?? "Unclassified";
        if (typeCounts.TryGetValue(type, out var count))
        {
            typeCounts[type] = count + 1;
        }
        else if (typeCounts.Count < maximumTrackedTypes)
        {
            typeCounts[type] = 1;
        }
        else
        {
            untrackedTypeElementCount++;
        }
    }

    return new
    {
        source = "model.xml",
        modelXmlBytes = modelEntry.Length,
        compressedModelXmlBytes = modelEntry.CompressedLength,
        elementCount,
        elementTypes = typeCounts
            .OrderBy(pair => pair.Key, StringComparer.Ordinal)
            .Select(pair => new { type = pair.Key, count = pair.Value })
            .ToArray(),
        maximumTrackedTypes,
        untrackedTypeElementCount,
        detail = "Bounded summary only; per-object metadata is emitted in the typed inventory collections."
    };
}

static string ResolveDacpac(string inputPath, string temporaryRoot, bool allowTrustedProjectBuild)
{
    if (Path.GetExtension(inputPath).Equals(".dacpac", StringComparison.OrdinalIgnoreCase))
    {
        return inputPath;
    }

    if (!Path.GetExtension(inputPath).Equals(".zip", StringComparison.OrdinalIgnoreCase))
    {
        throw new ArgumentException("Input must be a .dacpac or .zip file.");
    }

    var extractRoot = Path.Combine(temporaryRoot, "input");
    ExtractZipSafely(inputPath, extractRoot);
    var packagedDacpacs = FindFilesByExtension(extractRoot, ".dacpac");
    if (packagedDacpacs.Length == 1)
    {
        return packagedDacpacs[0];
    }
    if (packagedDacpacs.Length > 1)
    {
        throw new InvalidOperationException("The zip contains multiple DACPAC files; extract the desired DACPAC and pass its path directly.");
    }

    var projects = FindFilesByExtension(extractRoot, ".sqlproj");
    if (projects.Length != 1)
    {
        throw new InvalidOperationException("The zip must contain exactly one DACPAC or one SQL project.");
    }
    if (!allowTrustedProjectBuild)
    {
        throw new InvalidOperationException(
            "The zip contains a SQL project but no DACPAC. Building a SQL project executes its MSBuild targets and is disabled by default. " +
            "Build it in an isolated trusted environment and pass the DACPAC, or explicitly opt in with --allow-trusted-project-build only after reviewing and trusting the project.");
    }

    var buildRoot = Path.Combine(temporaryRoot, "build");
    Directory.CreateDirectory(buildRoot);
    var startInfo = new ProcessStartInfo("dotnet")
    {
        UseShellExecute = false,
        RedirectStandardOutput = true,
        RedirectStandardError = true
    };
    startInfo.ArgumentList.Add("build");
    startInfo.ArgumentList.Add(projects[0]);
    startInfo.ArgumentList.Add("--nologo");
    startInfo.ArgumentList.Add("--output");
    startInfo.ArgumentList.Add(buildRoot);

    Console.Error.WriteLine($"Building explicitly trusted SQL project '{projects[0]}'; its MSBuild targets and tasks will execute.");
    using var process = Process.Start(startInfo) ?? throw new InvalidOperationException("Unable to start dotnet build.");
    var standardOutputTask = process.StandardOutput.ReadToEndAsync();
    var standardErrorTask = process.StandardError.ReadToEndAsync();
    using var buildTimeout = new CancellationTokenSource(TimeSpan.FromMinutes(5));
    try
    {
        process.WaitForExitAsync(buildTimeout.Token).GetAwaiter().GetResult();
    }
    catch (OperationCanceledException)
    {
        process.Kill(entireProcessTree: true);
        Task.WaitAll(standardOutputTask, standardErrorTask);
        throw new TimeoutException("SQL project build exceeded the five-minute discovery limit.");
    }
    Task.WaitAll(standardOutputTask, standardErrorTask);
    var standardOutput = standardOutputTask.Result;
    var standardError = standardErrorTask.Result;
    if (process.ExitCode != 0)
    {
        throw new InvalidOperationException($"SQL project build failed.\n{standardOutput}\n{standardError}");
    }

    var builtDacpacs = FindFilesByExtension(buildRoot, ".dacpac");
    return builtDacpacs.Length == 1
        ? builtDacpacs[0]
        : throw new InvalidOperationException($"SQL project build produced {builtDacpacs.Length} DACPAC files; expected one.");
}

static string[] FindFilesByExtension(string root, string extension)
{
    return Directory.EnumerateFiles(root, "*", SearchOption.AllDirectories)
        .Where(path => Path.GetExtension(path).Equals(extension, StringComparison.OrdinalIgnoreCase))
        .ToArray();
}

static void ExtractZipSafely(string inputPath, string extractRoot)
{
    Directory.CreateDirectory(extractRoot);
    var extractionPrefix = Path.GetFullPath(extractRoot) + Path.DirectorySeparatorChar;
    var pathComparison = OperatingSystem.IsWindows()
        ? StringComparison.OrdinalIgnoreCase
        : StringComparison.Ordinal;
    using var archive = ZipFile.OpenRead(inputPath);
    foreach (var entry in archive.Entries)
    {
        var destinationPath = Path.GetFullPath(Path.Combine(extractRoot, entry.FullName));
        if (!destinationPath.StartsWith(extractionPrefix, pathComparison))
        {
            throw new InvalidDataException($"Zip entry escapes the extraction directory: {entry.FullName}");
        }

        if (string.IsNullOrEmpty(entry.Name))
        {
            Directory.CreateDirectory(destinationPath);
            continue;
        }

        Directory.CreateDirectory(Path.GetDirectoryName(destinationPath)!);
        entry.ExtractToFile(destinationPath, overwrite: false);
    }
}

static Dictionary<string, object?> CreateRecord(
    TSqlObject sourceObject,
    string stableId,
    string objectType,
    string? sourcePath,
    string? scriptError,
    BoundedBlindSpotCollection blindSpots,
    ModelCollationComparer identifierComparer)
{
    var recordWarnings = scriptError is null
        ? new List<string>()
        : new List<string> { "NonScriptableObject" };
    var dependencies = Array.Empty<string>();
    var dependencyExtractionComplete = true;
    try
    {
        dependencies = sourceObject.GetReferenced()
            .Select(GetStableId)
            .Where(dependency => !identifierComparer.Equals(dependency, stableId))
            .Distinct(identifierComparer)
            .OrderBy(dependency => dependency, identifierComparer)
            .ToArray();
    }
    catch (Exception exception)
    {
        dependencyExtractionComplete = false;
        recordWarnings.Add("DependencyExtractionFailed");
        blindSpots.Add(new
        {
            code = "DependencyExtractionFailed",
            sourceStableId = stableId,
            objectType,
            message = SanitizeMessage(exception.Message)
        });
    }

    return new Dictionary<string, object?>
    {
        ["sourceStableId"] = stableId,
        ["objectType"] = objectType,
        ["sourcePath"] = sourcePath,
        ["scriptable"] = scriptError is null && sourcePath is not null && dependencyExtractionComplete,
        ["scriptError"] = scriptError,
        ["dependencies"] = dependencies,
        ["dependencyExtractionComplete"] = dependencyExtractionComplete,
        ["warnings"] = recordWarnings.ToArray(),
        ["dacFxName"] = sourceObject.Name?.ToString()
    };
}

static void ApplySourceContractBlockers(
    List<object> conversionObjects,
    object[] sourceContracts,
    ModelCollationComparer identifierComparer)
{
    var blockersByProcedure = sourceContracts
        .Where(contract => !string.Equals(
            GetObjectProperty(contract, "status") as string,
            "Resolved",
            StringComparison.Ordinal))
        .GroupBy(
            contract => GetObjectProperty(contract, "referencingObject") as string ?? string.Empty,
            identifierComparer)
        .ToDictionary(group => group.Key, group => group.ToArray(), identifierComparer);

    foreach (var record in conversionObjects.OfType<Dictionary<string, object?>>())
    {
        var stableId = record["sourceStableId"] as string;
        if (string.IsNullOrWhiteSpace(stableId) ||
            !blockersByProcedure.TryGetValue(stableId, out var blockers))
        {
            continue;
        }

        record["scriptable"] = false;
        record["conversionStatus"] = "ManualReviewRequired";
        record["sourceContractBlockers"] = blockers.Select(contract => new
        {
            status = GetObjectProperty(contract, "status"),
            blocker = GetObjectProperty(contract, "blocker"),
            referencedObject = GetObjectProperty(contract, "referencedObject"),
            referencedName = GetObjectProperty(contract, "referencedName"),
            missingColumns = GetObjectProperty(contract, "missingColumns")
        }).ToArray();
    }
}

static object? GetObjectProperty(object value, string propertyName) =>
    value.GetType().GetProperty(propertyName)?.GetValue(value);

static object[] ExtractSourceContracts(
    TSqlModel model,
    BoundedBlindSpotCollection blindSpots,
    ModelCollationComparer identifierComparer)
{
    var contracts = new List<object>();
    foreach (var procedure in model.GetObjects(DacQueryScopes.UserDefined).Where(item => IsProcedure(item.ObjectType.Name)))
    {
        var procedureId = GetStableId(procedure);
        try
        {
            var dependencies = new Dictionary<string, SourceContractAccumulator>(identifierComparer);
            foreach (var relationship in procedure.GetReferencedRelationshipInstances()
                         .Where(item => item.Relationship.Name.Equals("BodyDependencies", StringComparison.OrdinalIgnoreCase)))
            {
                var referenced = relationship.Object;
                if (referenced is null)
                {
                    contracts.Add(new
                    {
                        referencingObject = procedureId,
                        referencedObject = (string?)null,
                        referencedObjectType = "Unknown",
                        referencedName = relationship.ObjectName?.ToString(),
                        referencedColumns = Array.Empty<string>(),
                        discoveredProjection = Array.Empty<string>(),
                        missingColumns = Array.Empty<string>(),
                        status = "UnknownProjection",
                        blocker = "UnresolvedSourceContractReference"
                    });
                    blindSpots.Add(new
                    {
                        code = "UnresolvedSourceContractReference",
                        sourceStableId = procedureId,
                        objectType = procedure.ObjectType.Name,
                        referencedName = relationship.ObjectName?.ToString(),
                        message = "DacFx did not resolve a procedure body dependency to a model object."
                    });
                    continue;
                }
                var referencedType = referenced.ObjectType.Name ?? "Unclassified";
                string? referencedColumn = null;
                if (IsColumn(referencedType))
                {
                    referencedColumn = GetObjectLeafName(referenced);
                    referenced = referenced.GetParent(DacQueryScopes.UserDefined);
                    if (referenced is null)
                    {
                        contracts.Add(new
                        {
                            referencingObject = procedureId,
                            referencedObject = (string?)null,
                            referencedObjectType = "Unknown",
                            referencedName = relationship.ObjectName?.ToString(),
                            referencedColumns = new[] { referencedColumn },
                            discoveredProjection = Array.Empty<string>(),
                            missingColumns = new[] { referencedColumn },
                            status = "UnknownProjection",
                            blocker = "UnresolvedSourceContractParent"
                        });
                        blindSpots.Add(new
                        {
                            code = "UnresolvedSourceContractParent",
                            sourceStableId = procedureId,
                            objectType = procedure.ObjectType.Name,
                            referencedName = relationship.ObjectName?.ToString(),
                            referencedColumn,
                            message = "DacFx did not resolve a referenced column to its parent table or view."
                        });
                        continue;
                    }
                    referencedType = referenced?.ObjectType.Name ?? "Unclassified";
                }
                if (referenced is null || !IsTableOrView(referencedType))
                {
                    contracts.Add(new
                    {
                        referencingObject = procedureId,
                        referencedObject = referenced is null ? null : (string?)GetStableId(referenced),
                        referencedObjectType = referencedType,
                        referencedName = relationship.ObjectName?.ToString(),
                        referencedColumns = string.IsNullOrWhiteSpace(referencedColumn)
                            ? Array.Empty<string>()
                            : new[] { referencedColumn },
                        discoveredProjection = Array.Empty<string>(),
                        missingColumns = string.IsNullOrWhiteSpace(referencedColumn)
                            ? Array.Empty<string>()
                            : new[] { referencedColumn },
                        status = "UnknownProjection",
                        blocker = "UnsupportedSourceContractReference"
                    });
                    continue;
                }

                var referencedId = GetStableId(referenced);
                if (!dependencies.TryGetValue(referencedId, out var dependency))
                {
                    dependency = new SourceContractAccumulator(referenced, NormalizeReferencedType(referencedType));
                    dependencies.Add(referencedId, dependency);
                }
                if (!string.IsNullOrWhiteSpace(referencedColumn))
                {
                    dependency.ReferencedColumns.Add(referencedColumn);
                }
            }

            foreach (var (referencedId, dependency) in dependencies.OrderBy(item => item.Key, identifierComparer))
            {
                var projection = GetOrderedProjection(dependency.ReferencedObject, dependency.ReferencedObjectType);
                var referencedColumns = dependency.ReferencedColumns
                    .Distinct(identifierComparer)
                    .OrderBy(column => column, identifierComparer)
                    .ToArray();
                var missingColumns = referencedColumns
                    .Where(column => !projection.Contains(column, identifierComparer))
                    .ToArray();
                contracts.Add(new
                {
                    referencingObject = procedureId,
                    referencedObject = referencedId,
                    referencedObjectType = dependency.ReferencedObjectType,
                    referencedColumns,
                    discoveredProjection = projection,
                    missingColumns,
                    status = projection.Length == 0
                        ? "UnknownProjection"
                        : missingColumns.Length == 0 ? "Resolved" : "MissingReferencedColumn"
                });
            }
        }
        catch (Exception exception)
        {
            contracts.Add(new
            {
                referencingObject = procedureId,
                referencedObject = (string?)null,
                referencedObjectType = "Unknown",
                referencedColumns = Array.Empty<string>(),
                discoveredProjection = Array.Empty<string>(),
                missingColumns = Array.Empty<string>(),
                status = "UnknownProjection",
                blocker = "SourceContractExtractionFailed"
            });
            blindSpots.Add(new
            {
                code = "SourceContractExtractionFailed",
                sourceStableId = procedureId,
                objectType = procedure.ObjectType.Name,
                message = SanitizeMessage(exception.Message)
            });
        }
    }
    return contracts.ToArray();
}

static string[] GetOrderedProjection(TSqlObject referencedObject, string referencedObjectType)
{
    var sourceObjectType = referencedObject.ObjectType.Name;
    var columns = string.Equals(sourceObjectType, "ExternalTable", StringComparison.OrdinalIgnoreCase)
        ? referencedObject.GetReferenced(ExternalTable.Columns, DacQueryScopes.UserDefined)
        : referencedObjectType == "Table"
            ? referencedObject.GetReferenced(Table.Columns, DacQueryScopes.UserDefined)
            : referencedObject.GetReferenced(View.Columns, DacQueryScopes.UserDefined);
    return columns.Select(GetObjectLeafName).ToArray();
}

static bool IsProcedure(string? objectType) =>
    objectType is not null && objectType.Contains("Procedure", StringComparison.OrdinalIgnoreCase);

static bool IsColumn(string? objectType) =>
    objectType is not null && objectType.Contains("Column", StringComparison.OrdinalIgnoreCase);

static bool IsTableOrView(string? objectType) =>
    objectType is not null &&
    (objectType.Equals("Table", StringComparison.OrdinalIgnoreCase) ||
     objectType.Equals("SqlTable", StringComparison.OrdinalIgnoreCase) ||
     objectType.Equals("ExternalTable", StringComparison.OrdinalIgnoreCase) ||
     objectType.Equals("View", StringComparison.OrdinalIgnoreCase) ||
     objectType.Equals("SqlView", StringComparison.OrdinalIgnoreCase));

static string NormalizeReferencedType(string objectType) =>
    objectType.Equals("View", StringComparison.OrdinalIgnoreCase) ||
    objectType.Equals("SqlView", StringComparison.OrdinalIgnoreCase)
        ? "View"
        : "Table";

static string GetObjectLeafName(TSqlObject sourceObject) =>
    sourceObject.Name?.Parts.LastOrDefault() ?? GetStableId(sourceObject);

static string GetStableId(TSqlObject sourceObject)
{
    var parts = sourceObject.Name?.Parts;
    return parts is { Count: > 0 }
        ? string.Join('.', parts)
        : $"{sourceObject.ObjectType.Name}:unnamed";
}

static ObjectCategory Classify(string objectType)
{
    string[] conversionTypes =
    [
        "Table", "SqlTable", "View", "SqlView", "Procedure", "SqlProcedure",
        "ScalarFunction", "TableValuedFunction", "Synonym", "Sequence",
        "ExternalTable", "ExternalDataSource", "ExternalFileFormat"
    ];
    string[] evidenceTypes =
    [
        "Schema", "Role", "DatabaseRole", "User", "Permission", "SecurityPolicy",
        "WorkloadGroup", "WorkloadClassifier"
    ];
    return conversionTypes.Contains(objectType, StringComparer.OrdinalIgnoreCase)
        ? ObjectCategory.Conversion
        : evidenceTypes.Contains(objectType, StringComparer.OrdinalIgnoreCase)
            ? ObjectCategory.Evidence
            : ObjectCategory.Supporting;
}

static string ToEvidenceFileName(string stableId)
{
    var invalid = Path.GetInvalidFileNameChars().ToHashSet();
    var safeStem = new string(stableId.Select(character => invalid.Contains(character) ? '_' : character).ToArray());
    safeStem = safeStem[..Math.Min(safeStem.Length, 100)];
    var stableHash = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(stableId))).ToLowerInvariant();
    return $"{safeStem}--{stableHash[..16]}";
}

enum ObjectCategory
{
    Conversion,
    Evidence,
    Supporting
}

sealed class SourceContractAccumulator(TSqlObject referencedObject, string referencedObjectType)
{
    public TSqlObject ReferencedObject { get; } = referencedObject;
    public string ReferencedObjectType { get; } = referencedObjectType;
    public List<string> ReferencedColumns { get; } = new();
}

sealed class ModelLoadFailureException(string[] attempts, Exception innerException)
    : Exception("DacFx could not load the DACPAC in either supported mode.", innerException)
{
    public string[] Attempts { get; } = attempts;
}

sealed class BoundedBlindSpotCollection
{
    private const int MaximumRetainedItems = 999;
    private const int MaximumSerializedBytes = 512 * 1024;
    private readonly List<object> retained = new();
    private int retainedSerializedBytes;
    private int totalObservedCount;

    public void Add(object value)
    {
        totalObservedCount++;
        var serializedBytes = JsonSerializer.SerializeToUtf8Bytes(value).Length;
        if (retained.Count >= MaximumRetainedItems
            || retainedSerializedBytes + serializedBytes > MaximumSerializedBytes)
        {
            return;
        }

        retained.Add(value);
        retainedSerializedBytes += serializedBytes;
    }

    public object[] ToArray()
    {
        var droppedCount = totalObservedCount - retained.Count;
        if (droppedCount == 0)
        {
            var completeEvidence = retained.ToArray();
            if (GetPersistedSize(completeEvidence) <= MaximumSerializedBytes)
            {
                return completeEvidence;
            }

            var lastIndex = retained.Count - 1;
            retainedSerializedBytes -= JsonSerializer.SerializeToUtf8Bytes(retained[lastIndex]).Length;
            retained.RemoveAt(lastIndex);
            droppedCount++;
        }

        while (true)
        {
            var truncationEvidence = new
            {
                code = "BlindSpotEvidenceTruncated",
                totalObservedCount,
                retainedCount = retained.Count,
                droppedCount,
                maximumRetainedItems = MaximumRetainedItems,
                maximumSerializedBytes = MaximumSerializedBytes
            };
            var candidate = retained.Append(truncationEvidence).ToArray();
            if (GetPersistedSize(candidate) <= MaximumSerializedBytes)
            {
                return candidate;
            }

            var lastIndex = retained.Count - 1;
            retainedSerializedBytes -= JsonSerializer.SerializeToUtf8Bytes(retained[lastIndex]).Length;
            retained.RemoveAt(lastIndex);
            droppedCount++;
        }
    }

    private static int GetPersistedSize(object[] evidence) =>
        JsonSerializer.SerializeToUtf8Bytes(
            evidence,
            new JsonSerializerOptions { WriteIndented = true }).Length;
}