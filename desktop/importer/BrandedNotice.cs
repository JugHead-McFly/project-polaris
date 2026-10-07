using System;
using System.Drawing;
using System.Windows.Forms;
namespace PolarisStandalone {
 internal sealed class BrandedNotice : Form {
  internal BrandedNotice(string title,string heading,string message) {
   Text=title; Icon=PolarisMark.WindowIcon(); ClientSize=new Size(560,300);
   AutoScaleMode=AutoScaleMode.Dpi; StartPosition=FormStartPosition.CenterScreen;
   FormBorderStyle=FormBorderStyle.FixedDialog; MaximizeBox=MinimizeBox=false;
   BackColor=Color.FromArgb(5,14,21); ForeColor=Color.FromArgb(238,242,234);
   Font=new Font("Segoe UI",10); Padding=new Padding(24);
   var grid=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=1,RowCount=3};
   grid.RowStyles.Add(new RowStyle(SizeType.Absolute,70));grid.RowStyles.Add(new RowStyle(SizeType.Percent,100));grid.RowStyles.Add(new RowStyle(SizeType.Absolute,44));Controls.Add(grid);
   var header=new Panel{Dock=DockStyle.Fill};header.Controls.Add(new PolarisMark{Size=new Size(58,58),Location=new Point(0,0)});
   header.Controls.Add(new Label{Text="Project Polaris",AutoSize=true,Location=new Point(74,0),Font=new Font("Segoe UI",20,FontStyle.Bold)});
   header.Controls.Add(new Label{Text=heading,AutoSize=true,Location=new Point(76,39),ForeColor=Color.FromArgb(83,216,205)});grid.Controls.Add(header,0,0);
   grid.Controls.Add(new Label{Text=message,Dock=DockStyle.Fill,Padding=new Padding(0,8,0,8),AutoEllipsis=false},0,1);
   var close=new Button{Text="Close",DialogResult=DialogResult.OK,Width=112,Dock=DockStyle.Right,FlatStyle=FlatStyle.Flat,BackColor=Color.FromArgb(83,216,205),ForeColor=Color.FromArgb(5,14,21),UseVisualStyleBackColor=false,AccessibleName="Close Polaris notice"};
   close.FlatAppearance.BorderSize=0;grid.Controls.Add(close,0,2);AcceptButton=CancelButton=close;
  }
  internal static void Show(string title,string heading,string message) { using(var dialog=new BrandedNotice(title,heading,message))dialog.ShowDialog(); }
 }
}
