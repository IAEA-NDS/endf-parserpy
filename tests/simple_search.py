from endf_parserpy import EndfDict, EndfParserCpp
import os

endf_path = "path/to/directory/with/ENDF-6/files"
files = os.listdir(endf_path)
paths = [os.path.join(endf_path, f) for f in files]
parser = EndfParserCpp(ignore_zero_mismatch=True, ignore_varspec_mismatch=True)


for f, p in zip(files, paths):
    try:
        endf_dict = parser.parsefile(p)
        mf3sec = endf_dict[3]
    except:
        print(f"error for {f}")
        continue
    for mt, sec in mf3sec.items():
        if 5 in sec["xstable"]["INT"]:
            print(f"{f}:  MT = {mt}")
