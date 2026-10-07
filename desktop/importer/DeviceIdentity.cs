using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Xml;
using Microsoft.Win32.SafeHandles;

namespace PolarisStandalone
{
    public sealed class DeviceEnrollment
    {
        public readonly string VolumeGuid, FileSystem, ReceiptRoot, NasRoot, StateRoot;
        public readonly uint VolumeSerial;
        public readonly bool AllowCleanup;
        internal DeviceEnrollment(string guid,uint serial,string fs,string receipt,string nas,string state,bool allow)
        { VolumeGuid=guid;VolumeSerial=serial;FileSystem=fs;ReceiptRoot=receipt;NasRoot=nas;StateRoot=state;AllowCleanup=allow; }
    }
    public sealed class DeviceVolume
    {
        public readonly string Root,VolumeGuid,FileSystem;
        public readonly uint VolumeSerial;
        public DeviceVolume(string root,string guid,uint serial,string fs)
        { Root=root;VolumeGuid=guid;VolumeSerial=serial;FileSystem=fs; }
    }
    public sealed class DeviceBinding
    {
        public readonly string CurrentRoot,ReceiptRoot,NasRoot,StateRoot,VolumeGuid,FileSystem;
        public readonly uint VolumeSerial;
        private readonly bool fixture=false;
        internal DeviceBinding(DeviceEnrollment e,string root)
        { CurrentRoot=root;ReceiptRoot=e.ReceiptRoot;NasRoot=e.NasRoot;StateRoot=e.StateRoot;VolumeGuid=e.VolumeGuid;VolumeSerial=e.VolumeSerial;FileSystem=e.FileSystem; }
#if CLEANUP_OFFLINE_FIXTURE
        private DeviceBinding(string current,string receipt,string nas,string state,DeviceVolume volume)
        { CurrentRoot=current;ReceiptRoot=receipt;NasRoot=nas;StateRoot=state;VolumeGuid=volume.VolumeGuid;VolumeSerial=volume.VolumeSerial;FileSystem=volume.FileSystem;fixture=true; }
        public static DeviceBinding ForFixture(string currentRoot,string receiptRoot,string nasRoot,string stateRoot)
        {
            currentRoot=Path.GetFullPath(currentRoot);nasRoot=Path.GetFullPath(nasRoot);stateRoot=Path.GetFullPath(stateRoot);receiptRoot=Path.GetFullPath(receiptRoot);
            string parent=FixtureParent(currentRoot);
            if(!DeviceIdentity.Same(parent,FixtureParent(nasRoot))||!DeviceIdentity.Same(parent,FixtureParent(stateRoot)))throw new ArgumentException("Fixture actual roots must share a unique TEMP parent.");
            foreach(string root in new[]{currentRoot,nasRoot,stateRoot})
                if(new DriveInfo(Path.GetPathRoot(root)).DriveType!=DriveType.Fixed)throw new ArgumentException("Fixture actual roots must be fixed local.");
            if(DeviceIdentity.Overlap(currentRoot,nasRoot)||DeviceIdentity.Overlap(currentRoot,stateRoot)||DeviceIdentity.Overlap(nasRoot,stateRoot))throw new ArgumentException("Fixture actual roots must be separate.");
            return new DeviceBinding(currentRoot,receiptRoot,nasRoot,stateRoot,DeviceIdentity.InspectVolume(Path.GetPathRoot(currentRoot)));
        }
        private static string FixtureParent(string root)
        {
            string temp=Path.GetFullPath(Path.GetTempPath()).TrimEnd('\\')+"\\";
            if(!root.StartsWith(temp,StringComparison.OrdinalIgnoreCase))throw new ArgumentException("Fixture outside TEMP.");
            string tail=root.Substring(temp.Length);int separator=tail.IndexOf('\\');
            if(separator<0)throw new ArgumentException("Fixture must have separate child roots.");
            string name=tail.Substring(0,separator);const string prefix="PolarisCleanupFixture-";Guid id;
            if(name.Length!=prefix.Length+32||!name.StartsWith(prefix,StringComparison.Ordinal)||!Guid.TryParseExact(name.Substring(prefix.Length),"N",out id))throw new ArgumentException("Unique cleanup fixture prefix required.");
            return temp+name;
        }
#endif
        public void ValidateCurrent()
        {
            if(fixture)
            {
                DeviceIdentity.CheckChain(CurrentRoot);
                if(!Directory.Exists(CurrentRoot))throw new IOException("Fixture source is absent.");
                return;
            }
            var drive=new DriveInfo(CurrentRoot);
            if(!drive.IsReady||drive.DriveType!=DriveType.Removable)throw new IOException("Enrolled DWARF is unavailable or not removable.");
            DeviceVolume current=DeviceIdentity.InspectVolume(CurrentRoot);
            if(!DeviceIdentity.Same(current.VolumeGuid,VolumeGuid)||current.VolumeSerial!=VolumeSerial||!DeviceIdentity.Same(current.FileSystem,FileSystem))throw new IOException("DWARF identity changed; no work admitted.");
            DeviceIdentity.CheckStructure(CurrentRoot);
        }
        public void AssertHandle(SafeFileHandle handle)
        {
            ValidateCurrent();
            DeviceIdentity.AssertNativeHandle(handle,CurrentRoot,VolumeSerial);
        }
    }
    public static class DeviceIdentity
    {
        public const string ApprovedNas=@"\\Synology_NAS\Astrophotography\Polaris_Inbox";
        public const string ApprovedState=@"G:\Polaris_Workspace\StandaloneHistory";
        public const string HistoricalReceiptRoot=@"I:\";
        public static DeviceEnrollment LoadEnrollment(string path)
        {
            if(!Path.IsPathRooted(path)||path.StartsWith(@"\\")||new DriveInfo(Path.GetPathRoot(path)).DriveType!=DriveType.Fixed)throw new IOException("Enrollment must be an ordinary fixed-local file.");
            CheckChain(path);
            using(var stream=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read))
            {
                if(stream.Length>8192)throw new InvalidDataException("Enrollment is too large.");
                var doc=new XmlDocument{XmlResolver=null};
                using(var reader=XmlReader.Create(stream,new XmlReaderSettings{DtdProcessing=DtdProcessing.Prohibit,XmlResolver=null,MaxCharactersInDocument=8192}))doc.Load(reader);
                XmlElement e=doc.DocumentElement;
                if(e==null||e.Name!="PolarisDeviceEnrollment"||e.GetAttribute("version")!="1"||e.ChildNodes.Count!=7)throw new InvalidDataException("Invalid device enrollment.");
                var names=new HashSet<string>(StringComparer.Ordinal);
                foreach(XmlNode child in e.ChildNodes)if(child.NodeType!=XmlNodeType.Element||!names.Add(child.Name))throw new InvalidDataException("Ambiguous enrollment fields.");
                string guid=Value(e,"VolumeGuid"),serial=Value(e,"VolumeSerial"),fs=Value(e,"FileSystem"),receipt=Value(e,"ReceiptRoot"),nas=Value(e,"NasRoot"),state=Value(e,"StateRoot"),allow=Value(e,"AllowCleanup");
                Guid id;
                if(guid.Length!=49||!guid.StartsWith(@"\\?\Volume{",StringComparison.OrdinalIgnoreCase)||!guid.EndsWith(@"}\",StringComparison.Ordinal)||!Guid.TryParseExact(guid.Substring(11,36),"D",out id))throw new InvalidDataException("Invalid enrolled volume GUID.");
                uint number;
                if(serial.Length!=8||!UInt32.TryParse(serial,System.Globalization.NumberStyles.AllowHexSpecifier,System.Globalization.CultureInfo.InvariantCulture,out number)||number==0)throw new InvalidDataException("Invalid enrolled volume serial.");
                if(String.IsNullOrWhiteSpace(fs)||fs.Length>32||!Same(receipt,HistoricalReceiptRoot)||!Same(nas,ApprovedNas)||!Same(state,ApprovedState)||(allow!="false"&&allow!="true"))throw new InvalidDataException("Enrollment roots or cleanup policy are outside approved configuration.");
                return new DeviceEnrollment(guid,number,fs,HistoricalReceiptRoot,ApprovedNas,ApprovedState,allow=="true");
            }
        }
        private static string Value(XmlElement e,string name){var n=e[name];if(n==null)throw new InvalidDataException("Missing enrollment field.");return n.InnerText;}
        public static DeviceBinding Discover(DeviceEnrollment enrollment)
        {
            if(enrollment==null)throw new ArgumentNullException("enrollment");
            var candidates=new List<DeviceVolume>();
            foreach(DriveInfo drive in DriveInfo.GetDrives())
            {
                if(drive.DriveType!=DriveType.Removable||!drive.IsReady)continue;
                candidates.Add(InspectVolume(drive.RootDirectory.FullName));
            }
            DeviceVolume match=Select(enrollment,candidates);
            if(match==null)return null;
            var binding=new DeviceBinding(enrollment,match.Root);binding.ValidateCurrent();return binding;
        }
        // Pure selection is testable without touching any real drive.
        internal static DeviceVolume Select(DeviceEnrollment enrollment,IEnumerable<DeviceVolume> candidates)
        {
            DeviceVolume match=null;
            foreach(var volume in candidates)
            {
                if(!Same(volume.VolumeGuid,enrollment.VolumeGuid))continue;
                if(volume.VolumeSerial!=enrollment.VolumeSerial||!Same(volume.FileSystem,enrollment.FileSystem))throw new IOException("Enrolled volume identity disagrees; inspection required.");
                if(match!=null)throw new IOException("Multiple enrolled-volume matches; no drive selected.");
                match=volume;
            }
            return match;
        }
        public static DeviceVolume InspectVolume(string root)
        {
            if(String.IsNullOrEmpty(root)||root.Length!=3||!Char.IsLetter(root[0])||root[1]!=':'||root[2]!='\\')throw new ArgumentException("A whole ordinary drive root is required.");
            CheckChain(root);
            var guid=new StringBuilder(128);var label=new StringBuilder(261);var fs=new StringBuilder(64);uint serial,max,flags;
            if(!GetVolumeNameForVolumeMountPoint(root,guid,(uint)guid.Capacity))throw new Win32Exception(Marshal.GetLastWin32Error(),"Cannot establish stable volume identity.");
            if(!GetVolumeInformation(root,label,label.Capacity,out serial,out max,out flags,fs,fs.Capacity))throw new Win32Exception(Marshal.GetLastWin32Error(),"Cannot read volume serial/filesystem.");
            return new DeviceVolume(root,guid.ToString(),serial,fs.ToString());
        }
        internal static void CheckStructure(string root)
        {
            CheckChain(root);
            foreach(string name in new[]{"Astronomy","Burst","Normal_Photos","Videos"})
            {string path=Path.Combine(root,name);CheckChain(path);if(!Directory.Exists(path))throw new IOException("Enrolled DWARF folder structure is unavailable.");}
        }
        internal static void CheckChain(string path)
        {
            for(string part=Path.GetFullPath(path);!String.IsNullOrEmpty(part);part=Path.GetDirectoryName(part))
                if((File.GetAttributes(part)&FileAttributes.ReparsePoint)!=0)throw new IOException("Redirected identity path refused.");
        }
        internal static bool Same(string a,string b){return String.Equals(a,b,StringComparison.OrdinalIgnoreCase);}
        internal static bool Overlap(string a,string b){return Same(a,b)||a.StartsWith(b.TrimEnd('\\')+"\\",StringComparison.OrdinalIgnoreCase)||b.StartsWith(a.TrimEnd('\\')+"\\",StringComparison.OrdinalIgnoreCase);}
        internal static void AssertNativeHandle(SafeFileHandle handle,string root,uint expectedSerial)
        {
            NativeInfo info;
            if(GetFileType(handle)!=1||!GetFileInformationByHandle(handle,out info))throw new IOException("Cannot identify source disk handle.");
            if(info.VolumeSerial!=expectedSerial||(info.Attributes&(0x10U|0x400U))!=0)throw new IOException("Source handle belongs to another volume or is not an ordinary file.");
            var buffer=new StringBuilder(32768);uint length=GetFinalPathNameByHandle(handle,buffer,(uint)buffer.Capacity,0);
            if(length==0||length>=buffer.Capacity)throw new IOException("Cannot resolve source handle path.");
            string final=buffer.ToString();
            if(!final.StartsWith(@"\\?\",StringComparison.Ordinal)||final.StartsWith(@"\\?\UNC\",StringComparison.OrdinalIgnoreCase)||!final.Substring(4).StartsWith(root.TrimEnd('\\')+"\\",StringComparison.OrdinalIgnoreCase))throw new IOException("Source handle escaped the enrolled volume root.");
        }
        [StructLayout(LayoutKind.Sequential)]private struct NativeTime{public uint Low,High;}
        [StructLayout(LayoutKind.Sequential)]private struct NativeInfo{public uint Attributes;public NativeTime Creation,Access,Write;public uint VolumeSerial,SizeHigh,SizeLow,Links,IndexHigh,IndexLow;}
        [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true,EntryPoint="GetVolumeNameForVolumeMountPointW")]private static extern bool GetVolumeNameForVolumeMountPoint(string path,StringBuilder volume,uint size);
        [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true,EntryPoint="GetVolumeInformationW")]private static extern bool GetVolumeInformation(string root,StringBuilder label,int labelSize,out uint serial,out uint max,out uint flags,StringBuilder fs,int fsSize);
        [DllImport("kernel32.dll",SetLastError=true)]private static extern uint GetFileType(SafeFileHandle handle);
        [DllImport("kernel32.dll",SetLastError=true)]private static extern bool GetFileInformationByHandle(SafeFileHandle handle,out NativeInfo info);
        [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true,EntryPoint="GetFinalPathNameByHandleW")]private static extern uint GetFinalPathNameByHandle(SafeFileHandle handle,StringBuilder path,uint size,uint flags);
    }
}
