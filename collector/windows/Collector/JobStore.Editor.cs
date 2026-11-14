using System.Text;
using System.Text.Json;

namespace Collector;

internal sealed partial class JobStore
{
    private static readonly string[] EditorOperations = ["inspect", "apply", "save", "reopen"];
    private static readonly string[] TextStyle = ["text", "font_family", "font_size", "font_bold", "font_italic", "alignment", "width", "color", "background", "background_padding", "background_corner", "stroke", "stroke_width", "line_spacing", "place"];
    private static readonly Dictionary<string, string[]> EditorMethods = new(StringComparer.Ordinal)
    {
        ["file.import"] = ["path"],
        ["clip.add"] = ["file_id", "layer", "position", "start", "end", "volume", "audio_only"],
        ["clip.set"] = ["id", "values"], ["clip.remove"] = ["id"], ["clip.split"] = ["id", "at"],
        ["clip.fade"] = ["id", "fade_in", "fade_out", "property", "value"],
        ["clip.keyframe.set"] = ["id", "property", "space", "unit", "at", "value", "interpolation"],
        ["text.add"] = [.. TextStyle, "layer", "position", "duration"], ["text.set"] = [.. TextStyle, "id", "this_clip_only"],
        ["effects.add"] = ["clip_id", "type"], ["effects.set"] = ["id", "values"],
        ["project.profile.set"] = ["values"]
    };
    private static void ValidateEditor(JsonElement inputs)
    {
        Protocol.Fields(inputs, "session_id", "operation", "request");
        string session = Protocol.Text(inputs, "session_id", 32), operation = Protocol.Text(inputs, "operation", 32);
        if (session.Length != 32 || session.Any(c => !char.IsAsciiHexDigit(c) || char.IsUpper(c)) || !EditorOperations.Contains(operation))
            throw new RequestError("invalid_editor_operation");
        var request = inputs.GetProperty("request");
        Protocol.Fields(request, operation switch { "inspect" => [], "apply" => ["commands", "base_revision"], "save" => ["path"], _ => ["path", "sha256"] });
        if (Encoding.UTF8.GetByteCount(Protocol.Canonical(request)) > 128 * 1024) throw new RequestError("editor_request_too_large");
        if (operation is "save" or "reopen")
        {
            string path = Protocol.Text(request, "path", 4096);
            if (!Path.IsPathFullyQualified(path) || path.StartsWith(@"\\", StringComparison.Ordinal) || Path.GetPathRoot(path) is not { Length: 3 })
                throw new RequestError("invalid_editor_path");
        }
        if (operation == "reopen")
        {
            string hash = Protocol.Text(request, "sha256", 64);
            if (hash.Length != 64 || hash.Any(c => !char.IsAsciiHexDigit(c) || char.IsUpper(c))) throw new RequestError("invalid_editor_digest");
        }
        if (operation != "apply") return;
        var revision = request.GetProperty("base_revision");
        if (revision.ValueKind != JsonValueKind.Number || !revision.TryGetInt64(out long number) || number < 0) throw new RequestError("invalid_editor_revision");
        var commands = request.GetProperty("commands");
        if (commands.ValueKind != JsonValueKind.Array || commands.GetArrayLength() is < 1 or > 128) throw new RequestError("invalid_editor_commands");
        BoundedEditorJson(commands);
        foreach (var command in commands.EnumerateArray())
        {
            Protocol.Fields(command, "method", "params", "as");
            string method = Protocol.Text(command, "method", 64);
            if (!EditorMethods.TryGetValue(method, out var parameters)) throw new RequestError("unsupported_editor_method");
            Protocol.Fields(command.GetProperty("params"), parameters);
        }
    }
    private static void BoundedEditorJson(JsonElement value, int depth = 0)
    {
        if (depth > 8) throw new RequestError("invalid_editor_json");
        switch (value.ValueKind)
        {
            case JsonValueKind.Object:
                if (value.EnumerateObject().Count() > 32) throw new RequestError("invalid_editor_json");
                var names = new HashSet<string>(StringComparer.Ordinal);
                foreach (var property in value.EnumerateObject())
                { if (!names.Add(property.Name)) throw new RequestError("invalid_editor_json"); BoundedEditorJson(property.Value, depth + 1); }
                break;
            case JsonValueKind.Array:
                if (value.GetArrayLength() > 256) throw new RequestError("invalid_editor_json");
                foreach (var item in value.EnumerateArray()) BoundedEditorJson(item, depth + 1);
                break;
            case JsonValueKind.String:
                string text = value.GetString()!;
                if (text.EnumerateRunes().Count() > 4096 || text.Contains('\0')) throw new RequestError("invalid_editor_json");
                break;
            case JsonValueKind.Number:
                if (!value.TryGetDouble(out double number) || !double.IsFinite(number) || Math.Abs(number) > 100_000_000) throw new RequestError("invalid_editor_json");
                break;
        }
    }
}
