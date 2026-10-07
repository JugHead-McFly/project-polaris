using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.IO;
public static class BuildIcon {
 public static void Main(string[] args) {
  string folder=args[0];int[] sizes={16,20,24,32,40,48,64,128,256};var bytes=new byte[sizes.Length][];
  for(int i=0;i<sizes.Length;i++)using(var bitmap=Render(sizes[i])) {
   bitmap.Save(Path.Combine(folder,"taskbar-"+sizes[i]+".png"),ImageFormat.Png);
   using(var stream=new MemoryStream()){bitmap.Save(stream,ImageFormat.Png);bytes[i]=stream.ToArray();}
  }
  using(var writer=new BinaryWriter(File.Create(Path.Combine(folder,"polaris-taskbar.ico")))) {
   writer.Write((ushort)0);writer.Write((ushort)1);writer.Write((ushort)sizes.Length);int offset=6+16*sizes.Length;
   for(int i=0;i<sizes.Length;i++){writer.Write((byte)(sizes[i]==256?0:sizes[i]));writer.Write((byte)(sizes[i]==256?0:sizes[i]));writer.Write((ushort)0);writer.Write((ushort)1);writer.Write((ushort)32);writer.Write(bytes[i].Length);writer.Write(offset);offset+=bytes[i].Length;}
   foreach(var payload in bytes)writer.Write(payload);
  }
  using(var preview=new Bitmap(760,260))using(var g=Graphics.FromImage(preview))using(var font=new Font("Segoe UI",11)) {
   g.Clear(Color.FromArgb(235,237,240));g.FillRectangle(Brushes.Black,0,130,760,130);
   for(int row=0;row<2;row++)for(int i=0;i<5;i++){int size=sizes[i];using(var b=Render(size)){g.DrawImageUnscaled(b,35+i*140,35+row*130);g.DrawString(size+" px",font,row==0?Brushes.Black:Brushes.White,30+i*140,93+row*130);}}
   preview.Save(Path.Combine(folder,"taskbar-preview.png"),ImageFormat.Png);
  }
 }
 static Bitmap Render(int size) {
  const int scale=4;using(var large=new Bitmap(size*scale,size*scale,PixelFormat.Format32bppArgb)) {
   using(var g=Graphics.FromImage(large)) {
    g.Clear(Color.Transparent);g.SmoothingMode=SmoothingMode.AntiAlias;g.ScaleTransform(size*scale/256f,size*scale/256f);
    float edge=Math.Max(6,256f/size*1.05f),ring=Math.Max(10,256f/size*1.55f);
    Color navy=Color.FromArgb(8,64,74),mint=Color.FromArgb(38,207,197);
    var state=g.Save();g.TranslateTransform(128,128);g.RotateTransform(-32);
    using(var halo=new Pen(Color.White,ring+edge+Math.Max(3,256f/size*.4f)))g.DrawEllipse(halo,-111,-47,222,94);
    using(var outline=new Pen(navy,ring+edge))g.DrawEllipse(outline,-111,-47,222,94);
    using(var inner=new Pen(mint,ring))g.DrawEllipse(inner,-111,-47,222,94);g.Restore(state);
    using(var star=new GraphicsPath()) {
     star.StartFigure();star.AddBezier(128,10,141,88,137,103,155,112);star.AddBezier(155,112,175,120,197,123,220,128);
     star.AddBezier(220,128,172,138,148,137,143,156);star.AddLine(143,156,128,246);star.AddLine(128,246,113,156);
     star.AddBezier(113,156,108,139,84,139,36,128);star.AddBezier(36,128,97,115,109,115,114,94);star.AddLine(114,94,128,10);star.CloseFigure();
     using(var halo=new Pen(Color.White,edge+Math.Max(3,256f/size*.4f))){halo.LineJoin=LineJoin.Round;g.DrawPath(halo,star);}
     using(var fill=new SolidBrush(mint))g.FillPath(fill,star);
     var clip=g.Save();g.SetClip(star);using(var facet=new SolidBrush(Color.FromArgb(86,237,218)))g.FillPolygon(facet,new[]{new Point(128,10),new Point(128,128),new Point(36,128)});g.Restore(clip);
     using(var outline=new Pen(navy,edge)){outline.LineJoin=LineJoin.Round;g.DrawPath(outline,star);}
    }
   }
   var result=new Bitmap(size,size,PixelFormat.Format32bppArgb);using(var g=Graphics.FromImage(result)){g.CompositingMode=CompositingMode.SourceCopy;g.InterpolationMode=InterpolationMode.HighQualityBicubic;g.PixelOffsetMode=PixelOffsetMode.HighQuality;g.DrawImage(large,new Rectangle(0,0,size,size));}return result;
  }
 }
}
