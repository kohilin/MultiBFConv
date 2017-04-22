

# Multilingual Back-and-Forth Conversion between Content and Function Head

- This converts dependency tree under the UD (http://universaldependencies.org) scheme back-and-forth between content and function head styles
- You can get better parsing accuracy by following steps
  - Convert UD to function head style
  - Train your parser with the converted data
  - Reconvert the parser's predictions into UD scheme
- Please check [1] in detail.

# HOW TO USE
python MultiBFConv.py input.conllu [forward|backward] output.conllu

- python3 MultiBFConv.py en-ud-dev.conllu forward en-ud-dev.conllu.conv
- python3 MultiBFConv.py en-ud-dev.conllu.conv backward en-ud-dev.conllu.reconv

# NOTE
- Please remove UD's extra lines like sentence id beforehand

# REFERENCE
[1] Ryosuke, Kohita., Hiroshi, Noji. & Yuji, Matsumoto. 2017. Multilingual Back-and-Forth Conversion between Content and Function Head for Easy Dependency Parsing. EACL.  
