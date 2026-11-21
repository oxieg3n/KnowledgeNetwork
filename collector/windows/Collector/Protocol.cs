using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Collector;

internal sealed class RequestError(string code, string? stage = null, int win32Error = 0) : Exception(code)
{
    public string? Stage { get; } = stage;
    public int Win32Error { get; } = win32Error;
}

internal static class Protocol
{
    public const string PipeName = "KnowledgeNetworkCollector-v1";
    public const int MaxBytes = 512 * 1024;
    public static readonly JsonSerializerOptions Json = new() { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower };
    public static string Encode(object value) => JsonSerializer.Serialize(value, Json);
    public static string Hash(string value) => Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(value)));
    public static void Fields(JsonElement value, params string[] names)
    {
        if (value.ValueKind != JsonValueKind.Object) throw new RequestError("object_required");
        var seen = new HashSet<string>();
        foreach (var item in value.EnumerateObject())
            if (!names.Contains(item.Name) || !seen.Add(item.Name)) throw new RequestError("unexpected_or_duplicate_field");
    }
    public static string Text(JsonElement value, string name, int limit)
    {
        if (!value.TryGetProperty(name, out var item) || item.ValueKind != JsonValueKind.String ||
            item.GetString() is not { } text || text.Length < 1 || text.Length > limit || text.Any(char.IsControl))
            throw new RequestError("invalid_" + name);
        return text;
    }
    public static string Canonical(JsonElement value) => value.ValueKind switch
    {
        JsonValueKind.Object => "{" + string.Join(",", value.EnumerateObject().OrderBy(p => p.Name, StringComparer.Ordinal)
            .Select(p => JsonSerializer.Serialize(p.Name) + ":" + Canonical(p.Value))) + "}",
        JsonValueKind.Array => "[" + string.Join(",", value.EnumerateArray().Select(Canonical)) + "]",
        JsonValueKind.String => JsonSerializer.Serialize(value.GetString()),
        _ => value.GetRawText()
    };
    public static async Task<string> ReadLine(Stream stream, CancellationToken token)
    {
        // A bounded frame prevents an authenticated but broken client from exhausting memory.
        using var buffer = new MemoryStream();
        byte[] chunk = new byte[4096];
        int received;
        while ((received = await stream.ReadAsync(chunk, token)) != 0)
        {
            int newline = Array.IndexOf(chunk, (byte)10, 0, received);
            int count = newline >= 0 ? newline : received;
            if (buffer.Length + count > MaxBytes) throw new RequestError("request_too_large");
            buffer.Write(chunk, 0, count);
            // Each connection executes one frame; trailing bytes never become another request.
            if (newline >= 0) return new UTF8Encoding(false, true).GetString(buffer.ToArray());
        }
        throw new RequestError("incomplete_request");
    }
    public static async Task WriteLine(Stream stream, string value, CancellationToken token) =>
        await stream.WriteAsync(Encoding.UTF8.GetBytes(value + "\n"), token);
}
