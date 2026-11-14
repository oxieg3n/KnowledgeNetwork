using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Collector;

internal sealed class RequestError(string code) : Exception(code);

internal static class Protocol
{
    public const string PipeName = "KnowledgeNetworkCollector-v1";
    public const int MaxBytes = 65536;
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
        _ => value.GetRawText()
    };
    public static async Task<string> ReadLine(Stream stream, CancellationToken token)
    {
        // A bounded frame prevents an authenticated but broken client from exhausting memory.
        using var buffer = new MemoryStream();
        byte[] one = new byte[1];
        while (await stream.ReadAsync(one, token) != 0)
        {
            if (one[0] == 10) return new UTF8Encoding(false, true).GetString(buffer.ToArray());
            if (buffer.Length >= MaxBytes) throw new RequestError("request_too_large");
            buffer.WriteByte(one[0]);
        }
        throw new RequestError("incomplete_request");
    }
    public static async Task WriteLine(Stream stream, string value, CancellationToken token) =>
        await stream.WriteAsync(Encoding.UTF8.GetBytes(value + "\n"), token);
}
