Add-Type @'
using System;
using System.Runtime.InteropServices;
using System.Collections.Generic;
using System.Text;
public static class PolarisCutoverNative {
 delegate bool EnumCallback(IntPtr h,IntPtr p);
 [DllImport("user32.dll")] static extern bool EnumWindows(EnumCallback callback,IntPtr p);
 [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern int GetClassName(IntPtr h,StringBuilder name,int size);
 public static uint IdleUiThread(uint process){
  var threads=new HashSet<uint>();bool visible=false;
  EnumWindows(delegate(IntPtr h,IntPtr p){uint owner;uint thread=GetWindowThreadProcessId(h,out owner);if(owner==process){var name=new StringBuilder(256);GetClassName(h,name,256);if(name.ToString().StartsWith("WindowsForms10.",StringComparison.Ordinal))threads.Add(thread);visible|=IsWindowVisible(h);}return true;},IntPtr.Zero);
  if(visible||threads.Count!=1)throw new InvalidOperationException("Expected one hidden detector UI thread.");
  foreach(uint t in threads)return t;throw new InvalidOperationException("No detector UI thread.");
 }
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h,out uint process);
 [DllImport("user32.dll",SetLastError=true)] public static extern bool PostMessage(IntPtr h,uint msg,IntPtr w,IntPtr l);
 [DllImport("user32.dll",SetLastError=true)] public static extern bool PostThreadMessage(uint thread,uint msg,IntPtr w,IntPtr l);
}
'@
