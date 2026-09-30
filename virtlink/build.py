"""Build the isolated public preview; never publish repository/server files."""
import base64, pathlib, shutil, subprocess
root=pathlib.Path(__file__).resolve().parent
out=root/'dist'
out.mkdir(exist_ok=True)
for name in ('index.html','style.css','app.js','investors.js','policies.js','mark.svg'):
    shutil.copyfile(root/name,out/name)
(out/'world.jpg').write_bytes(base64.b64decode((root/'world.b64').read_text(),validate=True))
subprocess.run(['npm','ci','--ignore-scripts'],cwd=root,check=True)
subprocess.run(['npm','run','build:accounts'],cwd=root,check=True)
for name in ('accounts.html','accounts.css'):
    shutil.copyfile(root/name,out/name)
