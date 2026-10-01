using System.Text.RegularExpressions;

public static class DedicatedPoolMessageSanitizer
{
    private const string SensitiveKeyPattern =
        "authorization|api[-_ ]?key|account[-_ ]?key|access[-_ ]?token|" +
        "refresh[-_ ]?token|client[-_ ]?secret|shared[-_ ]?access[-_ ]?(?:key|signature)|" +
        "(?:aws[-_ ]?)?secret[-_ ]?access[-_ ]?key|password|pwd|token|secret";

    public static string Sanitize(string message)
    {
        var sanitized = message.ReplaceLineEndings(" ").Trim();
        sanitized = Regex.Replace(
            sanitized,
            "(?i)([\"']?authorization[\"']?\\s*[:=]\\s*)\"\\s*(bearer|basic)\\s+(?:\\\\.|[^\"\\\\])*\"",
            match => $"{match.Groups[1].Value}{match.Groups[2].Value} \"[REDACTED]\"");
        sanitized = Regex.Replace(
            sanitized,
            "(?i)([\"']?authorization[\"']?\\s*[:=]\\s*)'\\s*(bearer|basic)\\s+(?:''|\\\\.|[^'\\\\])*'",
            match => $"{match.Groups[1].Value}{match.Groups[2].Value} '[REDACTED]'");
        sanitized = Regex.Replace(
            sanitized,
            $"(?i)([\"']?(?:{SensitiveKeyPattern})[\"']?\\s*[:=]\\s*(?:(?:bearer|basic)\\s+)?)\"(?:\\\\.|[^\"\\\\])*\"",
            match => $"{match.Groups[1].Value}\"[REDACTED]\"");
        sanitized = Regex.Replace(
            sanitized,
            $"(?i)([\"']?(?:{SensitiveKeyPattern})[\"']?\\s*[:=]\\s*(?:(?:bearer|basic)\\s+)?)'(?:''|\\\\.|[^'\\\\])*'",
            match => $"{match.Groups[1].Value}'[REDACTED]'");
        sanitized = Regex.Replace(
            sanitized,
            $"(?i)([\"']?(?:{SensitiveKeyPattern})[\"']?\\s*[:=]\\s*(?:bearer|basic)\\s+)(?![\"'])[^;\\r\\n]+",
            "$1[REDACTED]");
        sanitized = Regex.Replace(
            sanitized,
            $"(?i)([\"']?(?:{SensitiveKeyPattern})[\"']?\\s*[:=](?>\\s*))(?!(?:bearer|basic)\\b)[^;\\r\\n]+",
            "$1[REDACTED]");
        sanitized = Regex.Replace(
            sanitized,
            $"(?i)([?&#](?:{SensitiveKeyPattern}|sig|se|sp|spr|srt|sv)=)[^&\\s]+",
            "$1[REDACTED]");
        return sanitized.Length > 500 ? $"{sanitized[..497]}..." : sanitized;
    }
}
