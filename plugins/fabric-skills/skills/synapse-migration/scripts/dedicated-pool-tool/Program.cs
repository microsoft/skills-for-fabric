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
    var loadOptions = new ModelLoadOptions
    {
        LoadAsScriptBackedModel = true
    };

    using var model = TSqlModel.LoadFromDacpac(dacpacPath, loadOptions);
    var modelMetadata = ExtractModelMetadata(dacpacPath);
    var conversionObjects = new List<object>();
    var evidenceObjects = new List<object>();
    var supportingObjects = new List<object>();
    var warnings = new List<object>();
    Directory.CreateDirectory(Path.Combine(outputPath, "source"));

    foreach (var sourceObject in model.GetObjects(DacQueryScopes.UserDefined))
    {
        var objectType = sourceObject.ObjectType.Name ?? "Unclassified";
        var stableId = GetStableId(sourceObject);
        var category = Classify(objectType);

        if (category == ObjectCategory.Supporting)
        {
            supportingObjects.Add(CreateRecord(sourceObject, stableId, objectType, null, null, warnings));
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
            scriptError = exception.Message;
            warnings.Add(new
            {
                code = "NonScriptableObject",
                sourceStableId = stableId,
                objectType,
                message = exception.Message
            });
        }

        string? sourcePath = null;
        if (!string.IsNullOrWhiteSpace(sourceText))
        {
            sourcePath = Path.Combine("source", $"{ToEvidenceFileName(stableId)}.sql").Replace('\\', '/');
            File.WriteAllText(Path.Combine(outputPath, sourcePath), sourceText);
        }

        var record = CreateRecord(sourceObject, stableId, objectType, sourcePath, scriptError, warnings);
        if (category == ObjectCategory.Conversion)
        {
            conversionObjects.Add(record);
        }
        else
        {
            evidenceObjects.Add(record);
        }
    }

    var sourceContracts = ExtractSourceContracts(model, warnings);
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
            loadAsScriptBackedModel = true,
            queryScope = "UserDefined"
        },
        modelMetadata,
        objects = conversionObjects,
        evidenceObjects,
        supportingObjects,
        sourceContracts,
        blindSpots = warnings
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
    var message = exception.Message.ReplaceLineEndings(" ").Trim();
    if (message.Length > 500)
    {
        message = $"{message[..497]}...";
    }
    Console.Error.WriteLine($"Dedicated Pool discovery failed: {message}");
    return 1;
}

static void TryDeleteDirectory(string path)
{
    try
    {
        Directory.Delete(path, recursive: true);
    }
    catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
    {
        Console.Error.WriteLine($"Warning: temporary directory cleanup failed: {exception.Message}");
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

static object CreateRecord(
    TSqlObject sourceObject,
    string stableId,
    string objectType,
    string? sourcePath,
    string? scriptError,
    List<object> blindSpots)
{
    var recordWarnings = scriptError is null
        ? new List<string>()
        : new List<string> { "NonScriptableObject" };
    var dependencies = Array.Empty<string>();
    try
    {
        dependencies = sourceObject.GetReferenced()
            .Select(GetStableId)
            .Where(dependency => !dependency.Equals(stableId, StringComparison.OrdinalIgnoreCase))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .OrderBy(dependency => dependency, StringComparer.OrdinalIgnoreCase)
            .ToArray();
    }
    catch (Exception exception)
    {
        recordWarnings.Add("DependencyExtractionFailed");
        blindSpots.Add(new
        {
            code = "DependencyExtractionFailed",
            sourceStableId = stableId,
            objectType,
            message = exception.Message
        });
    }

    return new
    {
        sourceStableId = stableId,
        objectType,
        sourcePath,
        scriptable = scriptError is null && sourcePath is not null,
        scriptError,
        dependencies,
        warnings = recordWarnings.ToArray(),
        dacFxName = sourceObject.Name?.ToString()
    };
}

static object[] ExtractSourceContracts(TSqlModel model, List<object> blindSpots)
{
    var contracts = new List<object>();
    foreach (var procedure in model.GetObjects(DacQueryScopes.UserDefined).Where(item => IsProcedure(item.ObjectType.Name)))
    {
        var procedureId = GetStableId(procedure);
        try
        {
            var dependencies = new Dictionary<string, SourceContractAccumulator>(StringComparer.OrdinalIgnoreCase);
            foreach (var relationship in procedure.GetReferencedRelationshipInstances()
                         .Where(item => item.Relationship.Name.Equals("BodyDependencies", StringComparison.OrdinalIgnoreCase)))
            {
                var referenced = relationship.Object;
                if (referenced is null)
                {
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

            foreach (var (referencedId, dependency) in dependencies.OrderBy(item => item.Key, StringComparer.OrdinalIgnoreCase))
            {
                var projection = GetOrderedProjection(dependency.ReferencedObject, dependency.ReferencedObjectType);
                var referencedColumns = dependency.ReferencedColumns
                    .Distinct(StringComparer.OrdinalIgnoreCase)
                    .OrderBy(column => column, StringComparer.OrdinalIgnoreCase)
                    .ToArray();
                var missingColumns = referencedColumns
                    .Where(column => !projection.Contains(column, StringComparer.OrdinalIgnoreCase))
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
            blindSpots.Add(new
            {
                code = "SourceContractExtractionFailed",
                sourceStableId = procedureId,
                objectType = procedure.ObjectType.Name,
                message = exception.Message
            });
        }
    }
    return contracts.ToArray();
}

static string[] GetOrderedProjection(TSqlObject referencedObject, string referencedObjectType)
{
    var columns = referencedObjectType == "Table"
        ? referencedObject.GetReferenced(Table.Columns, DacQueryScopes.UserDefined)
        : referencedObject.GetReferenced(View.Columns, DacQueryScopes.UserDefined);
    return columns.Select(GetObjectLeafName).ToArray();
}

static bool IsProcedure(string? objectType) =>
    objectType is not null && objectType.Contains("Procedure", StringComparison.OrdinalIgnoreCase);

static bool IsColumn(string? objectType) =>
    objectType is not null && objectType.Contains("Column", StringComparison.OrdinalIgnoreCase);

static bool IsTableOrView(string? objectType) =>
    objectType is not null && (objectType.Contains("Table", StringComparison.OrdinalIgnoreCase) ||
                               objectType.Contains("View", StringComparison.OrdinalIgnoreCase));

static string NormalizeReferencedType(string objectType) =>
    objectType.Contains("View", StringComparison.OrdinalIgnoreCase) ? "View" : "Table";

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