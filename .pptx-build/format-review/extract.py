import sys, zipfile, re
from pathlib import Path
from xml.etree import ElementTree as ET
from pypdf import PdfReader
root=Path(r'C:\Users\Rohit Arya\Desktop\Ai_Project')
for name in ['Campus_Navigation_Assistant_Final_Report.pdf','Campus_Navigation_Assistant_Final_Presentation.pptx','Campus_Navigation_Assistant_Final_Presentation_CrowdAware.pptx','Campus_Navigation_Assistant_Final_Presentation_ClearLabels.pptx']:
 p=root/name
 if p.suffix=='.pdf':
  d=PdfReader(str(p)); print(f'PDF {name}: pages={len(d.pages)} size={p.stat().st_size}');
  for i,page in enumerate(d.pages):
   tx=page.extract_text() or ''
   headings=[line.strip() for line in tx.splitlines() if re.match(r'^(\d+\.|Abstract|References|Keywords|Conclusion|FINAL PROJECT)',line.strip())]
   print(f'  p{i+1}: chars={len(tx)} headings={headings}')
 else:
  with zipfile.ZipFile(p) as z:
   slides=sorted([x for x in z.namelist() if re.match(r'ppt/slides/slide\d+\.xml$',x)],key=lambda x:int(re.search(r'\d+',x).group()))
   print(f'PPT {name}: slides={len(slides)}')
   ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
   for i,s in enumerate(slides):
    rt=ET.fromstring(z.read(s)); paras=[]
    for pnode in rt.findall('.//a:p',ns):
     val=''.join(t.text or '' for t in pnode.findall('.//a:t',ns)).strip()
     if val: paras.append(val)
    print(f'  {i+1:02}: '+ ' | '.join(paras))

