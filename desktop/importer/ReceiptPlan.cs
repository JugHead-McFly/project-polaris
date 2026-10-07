using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Xml;

namespace PolarisStandalone
{
    // Load reads local evidence only. LoadBound additionally validates device identity;
    // neither follows historical source paths, creates files, nor deletes anything.
    public static class ReceiptPlan
    {
        private sealed class Row
        {
            public string Operation, Id, Key, Source, Destination, Relative, Hash, ReceiptHash, ReceiptPath;
            public long Length, SourceTicks, DestinationTicks;
        }
        public static List<CleanupRequest> LoadBound(DeviceBinding binding)
        {
            if (binding == null) throw new ArgumentNullException("binding");
            binding.ValidateCurrent();
            List<CleanupRequest> requests = LoadForCleanup(binding.StateRoot, binding.ReceiptRoot, binding.NasRoot);
            foreach (CleanupRequest request in requests)
            {
                request.SourceRoot = binding.CurrentRoot;
                request.ReceiptSourceRoot = binding.ReceiptRoot;
                request.Binding = binding;
            }
            return requests;
        }
        public static List<CleanupRequest> LoadForCleanup(string stateRoot, string sourceRoot, string nasRoot)
        {
            var requests = Load(stateRoot, sourceRoot, nasRoot);
            requests.RemoveAll(delegate(CleanupRequest r) { return CalibrationVersions.IsCalibration(r.RelativePath); });
            return requests;
        }
        public static List<CleanupRequest> Load(string stateRoot, string sourceRoot, string nasRoot)
        {
            if (String.IsNullOrWhiteSpace(stateRoot) || !Path.IsPathRooted(stateRoot) || stateRoot.StartsWith(@"\\",StringComparison.Ordinal) || Path.GetPathRoot(stateRoot).Length < 3)
                throw new InvalidDataException("Copying history must be an absolute ordinary local root.");
            stateRoot=Path.GetFullPath(stateRoot);
            if(new DriveInfo(Path.GetPathRoot(stateRoot)).DriveType!=DriveType.Fixed)throw new InvalidDataException("Copying history must be on a fixed local drive.");
            for(string part=stateRoot;!String.IsNullOrEmpty(part);part=Path.GetDirectoryName(part))
                if((File.GetAttributes(part)&FileAttributes.ReparsePoint)!=0)throw new InvalidDataException("Redirected copying-history ancestor refused.");
            var intents = new Dictionary<string, Row>(StringComparer.Ordinal);
            var confirmed = new Dictionary<string, Row>(StringComparer.Ordinal);
            var intentKeys = new HashSet<string>(StringComparer.Ordinal);
            var confirmedKeys = new HashSet<string>(StringComparer.Ordinal);
            foreach (string path in Directory.GetFiles(stateRoot, "receipt-*.xml"))
            {
                if ((File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0) throw new InvalidDataException("Redirected receipt refused.");
                byte[] bytes = File.ReadAllBytes(path);
                if (bytes.Length > 65536) throw new InvalidDataException("Receipt too large.");
                var document = new XmlDocument { XmlResolver = null };
                using (var memory = new MemoryStream(bytes))
                using (var reader = XmlReader.Create(memory, new XmlReaderSettings { DtdProcessing = DtdProcessing.Prohibit, XmlResolver = null, MaxCharactersInDocument = 65536 })) document.Load(reader);
                XmlElement e = document.DocumentElement;
                if (e == null || e.Name != "PolarisCopyReceipt" || e.GetAttribute("version") != "1" || e.ChildNodes.Count != 11) throw new InvalidDataException("Malformed copying receipt.");
                var names = new HashSet<string>(StringComparer.Ordinal);
                foreach (XmlNode child in e.ChildNodes) if (child.NodeType != XmlNodeType.Element || !names.Add(child.Name)) throw new InvalidDataException("Ambiguous copying receipt.");
                string operation = Value(e, "Operation");
                if (operation == "hold" || operation == "reuse") continue;
                if (operation != "intent" && operation != "confirmed") throw new InvalidDataException("Unknown copying receipt operation.");
                var row = new Row { Operation = operation, Id = Value(e,"Id"), Key = Value(e,"Key"), Source = Value(e,"Source"), Destination = Value(e,"Destination"), Relative = Value(e,"Relative"), Hash = Value(e,"Hash"), ReceiptHash = Sha(bytes), ReceiptPath = path, Length = Number(e,"Length"), SourceTicks = Number(e,"SourceTicks"), DestinationTicks = Number(e,"DestinationTicks") };
                if (!Hex(row.Id,32) || !Hex(row.Key,64) || row.Length <= 0) throw new InvalidDataException("Invalid copying identity or length.");
                LegalRelative(row.Relative);
                string source = Path.GetFullPath(Path.Combine(sourceRoot,row.Relative)), destination = Path.GetFullPath(Path.Combine(nasRoot,row.Relative));
                string key = Sha(Encoding.UTF8.GetBytes(CanonicalRoot(sourceRoot).ToUpperInvariant()+"\n"+CanonicalRoot(nasRoot).ToUpperInvariant()+"\n"+row.Relative.ToUpperInvariant()));
                if (!String.Equals(destination, row.Destination, StringComparison.OrdinalIgnoreCase))
                {
                    string versionHash = CalibrationVersions.ValidateDestination(nasRoot, row.Relative, row.Destination);
                    destination = CalibrationVersions.Destination(nasRoot, row.Relative, versionHash);
                    key = CalibrationVersions.Key(sourceRoot, nasRoot, row.Relative, versionHash);
                    if (operation == "confirmed" && row.Hash != versionHash) throw new InvalidDataException("Calibration version/hash mismatch.");
                }
                if (!String.Equals(source,row.Source,StringComparison.OrdinalIgnoreCase) || !String.Equals(destination,row.Destination,StringComparison.OrdinalIgnoreCase) || key != row.Key) throw new InvalidDataException("Copying receipt route differs from approved roots.");
                var bucket = operation == "intent" ? intents : confirmed;
                var keys = operation == "intent" ? intentKeys : confirmedKeys;
                if (bucket.ContainsKey(row.Id) || !keys.Add(row.Key)) throw new InvalidDataException("Duplicate or ambiguous copying reservation.");
                bucket.Add(row.Id,row);
            }
            var result = new List<CleanupRequest>();
            foreach (Row row in confirmed.Values)
            {
                Row intent;
                if (!intents.TryGetValue(row.Id,out intent) || !String.Equals(intent.Destination,row.Destination,StringComparison.OrdinalIgnoreCase) || !String.Equals(intent.Source,row.Source,StringComparison.OrdinalIgnoreCase) || intent.Key != row.Key || intent.Relative != row.Relative || intent.Length != row.Length || intent.SourceTicks != row.SourceTicks || row.SourceTicks <= 0 || row.DestinationTicks <= 0 || !Hex(row.Hash,64)) throw new InvalidDataException("Confirmation does not match its copying intent.");
                string top = row.Relative.Split('\\','/')[0];
                if (top != "Astronomy" && top != "Burst" && top != "Normal_Photos" && top != "Videos") continue;
                result.Add(new CleanupRequest { SourceRoot=sourceRoot, NasRoot=nasRoot, StateRoot=stateRoot, RelativePath=row.Relative, CopyDestination=row.Destination, ExpectedLength=row.Length, ExpectedSha256=row.Hash, AcceptedReceiptSha256=row.ReceiptHash, AcceptedReceiptPath=row.ReceiptPath });
            }
            if (intents.Count != confirmed.Count) throw new InvalidDataException("Unresolved copying intent blocks cleanup planning.");
            result.Sort(delegate(CleanupRequest a,CleanupRequest b) { return StringComparer.OrdinalIgnoreCase.Compare(a.RelativePath,b.RelativePath); });
            return result;
        }
        private static string CanonicalRoot(string root)
        { string full=Path.GetFullPath(root); return full.Length == Path.GetPathRoot(full).Length ? full : full.TrimEnd('\\','/'); }
        private static string Value(XmlElement e,string name)
        { var n=e[name]; if(n==null) throw new InvalidDataException("Missing receipt field."); return n.InnerText; }
        private static long Number(XmlElement e,string name) { return Int64.Parse(Value(e,name),CultureInfo.InvariantCulture); }
        private static bool Hex(string value,int length)
        { if(value.Length!=length)return false; foreach(char c in value) if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return false; return true; }
        private static string Sha(byte[] bytes)
        { using(var hash=SHA256.Create()) return BitConverter.ToString(hash.ComputeHash(bytes)).Replace("-","").ToLowerInvariant(); }
        private static void LegalRelative(string relative)
        {
            if(String.IsNullOrEmpty(relative)||Path.IsPathRooted(relative))throw new InvalidDataException("Invalid relative source path.");
            foreach(string part in relative.Split('\\','/'))
                if(part.Length==0||part=="."||part==".."||part.EndsWith(".")||part.EndsWith(" ")||part.IndexOfAny(Path.GetInvalidFileNameChars())>=0)throw new InvalidDataException("Unsafe relative source component.");
        }
    }
}
