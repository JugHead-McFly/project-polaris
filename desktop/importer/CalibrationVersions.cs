using System;
using System.IO;
using System.Text;
using System.Security.Cryptography;

namespace PolarisStandalone
{
    public static class CalibrationVersions
    {
        public static bool IsCalibration(string relative)
        {
            if (relative == null) return false;
            string r = relative.Replace('/', '\\');
            return r.StartsWith("Astronomy\\CALI_FRAME\\", StringComparison.OrdinalIgnoreCase) ||
                r.StartsWith("Astronomy\\DWARF_DARK\\", StringComparison.OrdinalIgnoreCase);
        }
        public static string Destination(string root, string relative, string hash)
        {
            if (!IsCalibration(relative) || !IsHash(hash)) throw new InvalidDataException("Invalid calibration version.");
            string original = Path.GetFullPath(Path.Combine(root, relative));
            return Path.Combine(Path.GetDirectoryName(original), Path.GetFileNameWithoutExtension(original) + "__sha256-" + hash + Path.GetExtension(original));
        }
        public static string ValidateDestination(string root, string relative, string destination)
        {
            string stem = Path.GetFileNameWithoutExtension(destination);
            if (stem.Length < 73) throw new InvalidDataException("Invalid version destination.");
            string hash = stem.Substring(stem.Length - 64);
            if (!String.Equals(Destination(root, relative, hash), destination, StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException("Calibration version escaped its exact route.");
            return hash;
        }
        public static string Key(string source, string nas, string relative, string hash)
        {
            string text = Canonical(source).ToUpperInvariant() + "\n" + Canonical(nas).ToUpperInvariant() + "\n" + relative.ToUpperInvariant() + "\ncalibration-sha256:" + hash;
            using (var sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(text))).Replace("-", "").ToLowerInvariant();
        }
        static string Canonical(string root) { string p = Path.GetFullPath(root); return p.Length == Path.GetPathRoot(p).Length ? p : p.TrimEnd('\\', '/'); }
        static bool IsHash(string h) { if (h == null || h.Length != 64) return false; foreach (char c in h) if (!(c >= '0' && c <= '9') && !(c >= 'a' && c <= 'f')) return false; return true; }
    }
}
