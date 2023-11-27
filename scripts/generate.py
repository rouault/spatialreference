#!/usr/bin/env python

import json
import os, shutil
import re
from pathlib import Path
from string import Template 

import pyproj
#from contextlib import redirect_stdout

def substitute(src_filename, dst_folder, dic):
    Path(dst_folder).mkdir(parents=True, exist_ok=True)
    dst_folder += '/index.html'
    
    with open(src_filename, 'r') as src, open(dst_folder, 'w') as dst:
        txt = Template(src.read())
        result = txt.substitute(dic)
        dst.write(result)


def dump(dst_folder, txt):
    Path(dst_folder).mkdir(parents=True, exist_ok=True)
    dst_folder += '/index.html'
    
    with open(dst_folder, 'w') as dst:
        dst.write(txt)


if __name__ == '__main__':
    dest_dir = os.getenv('DEST_DIR', '.')
    dest_file = f'{dest_dir}/crslist.json'
    templates = './templates'

    pyproj_versions = pyproj.show_versions()

    crs_list = pyproj.database.query_crs_info(allow_deprecated=True)

    crss = sorted(
        [crs._asdict() for crs in crs_list if crs.area_of_use],
        key=lambda d: d['auth_name'] + d['code'].zfill(7)
    )

    print('\nAnalysis of duplicated codes')
    codes = [d['auth_name'] + ':' + d['code'] for d in crss]
    unique = []
    for code in codes:
        if code in unique:
            print(code + ' is duplicated')
        else:
            unique.append(code)

    with open(dest_file, 'w') as fp:
        json.dump(crss, fp, indent=2, default=lambda o: str(o).replace('PJType.', ''))

    shutil.copy(f'{templates}/sr_logo.jpg', dest_dir)
    for literal in ['base.js', 'base.css']:
        shutil.copy(f'{templates}/{literal}', dest_dir)
    
    dic = {'version': os.getenv('PROJ_VERSION', '.'),
           'home_dir': '.'}
    substitute(f'{templates}/index.tmpl', f'{dest_dir}', dic)
    dic['home_dir'] = '..'
    substitute(f'{templates}/about.tmpl', f'{dest_dir}/about', dic)
    substitute(f'{templates}/ref.tmpl', f'{dest_dir}/ref', dic)

    count = 0
    for id, c in enumerate(crss):
        count += 1
        if count > 10:
            break
        code=c["code"]
        auth_name=c["auth_name"]
        name = c["name"]
        auth_lowercase = auth_name.lower()
        crs = pyproj.CRS.from_authority(auth_name=auth_name, code=code)
        epsg_a = ''
        if auth_name == "EPSG":
            scapedName = re.sub(r'[^0-9a-zA-Z]+', '-', name);
            epsg_a = f'<a href="https://epsg.org/crs_{code}/{scapedName}.html">epsg.org</a>'
        bounds = ', '.join([str(x) for x in c["area_of_use"][:4]])
        full_name = lambda c: f'{c["auth_name"]}:{c["code"]} : {c["name"]}'
        url = lambda c: f'../../../ref/{c["auth_name"].lower()}/{c["code"]}'
        dic = {'home_dir': '../../..',
               'authority': auth_name,
               'code': code,
               'name': name,
               'area_name': c["area_of_use"][4],
               'epsg_a': epsg_a,
               'bounds': bounds,
               'scope': crs.scope,
               'prev_full_name': full_name(crss[id-1]),
               'prev_url': url(crss[id-1]),
               'next_full_name': full_name(crss[id+1]),
               'next_url': url(crss[id+1]),
        }
        substitute(f'{templates}/crs.tmpl', f'{dest_dir}/ref/{auth_lowercase}/{code}', dic)

        try:
            output_axis_rule = True if crs.is_projected else None
            pretty = crs.to_wkt(version='WKT1_GDAL', pretty=True, output_axis_rule=output_axis_rule)
            ogcwkt = crs.to_wkt(version='WKT1_GDAL', pretty=False, output_axis_rule=output_axis_rule)
        except:
            pretty = 'This CRS cannot be written as WKT1_GDAL'
            ogcwkt = 'This CRS cannot be written as WKT1_GDAL'

        pretty2 = crs.to_wkt(version='WKT2_2019', pretty=True, output_axis_rule=output_axis_rule)
        ogcwkt2 = crs.to_wkt(version='WKT2_2019', pretty=False, output_axis_rule=output_axis_rule)

        dic = {'home_dir': '../../../..',
               'authority': auth_name,
               'code': code,
               'syntax_html': pretty,
        }
        substitute(f'{templates}/html.tmpl', f'{dest_dir}/ref/{auth_lowercase}/{code}/html', dic)
        dump(f'{dest_dir}/ref/{auth_lowercase}/{code}/prettywkt', pretty)
        dump(f'{dest_dir}/ref/{auth_lowercase}/{code}/ogcwkt', ogcwkt)

        dic = {'home_dir': '../../../..',
               'authority': auth_name,
               'code': code,
               'syntax_html': pretty2,
        }
        substitute(f'{templates}/html.tmpl', f'{dest_dir}/ref/{auth_lowercase}/{code}/htmlwkt2', dic)
        dump(f'{dest_dir}/ref/{auth_lowercase}/{code}/prettywkt2', pretty2)
        dump(f'{dest_dir}/ref/{auth_lowercase}/{code}/ogcwkt2', ogcwkt2)

        try:
            esri = crs.to_wkt(version='WKT1_ESRI')
        except:
            esri = 'This CRS cannot be written as WKT1_ESRI'
        dump(f'{dest_dir}/ref/{auth_lowercase}/{code}/esriwkt', esri)

        json = crs.to_json(pretty=True)
        dump(f'{dest_dir}/ref/{auth_lowercase}/{code}/json', json)

        try:
            proj4 = crs.to_proj4()
        except:
            proj4 = ''
        dump(f'{dest_dir}/ref/{auth_lowercase}/{code}/proj4', proj4)

    exit(0)

    types = ({'path': 'wkt1', 'version': 'WKT1_GDAL'},
             {'path': 'wkt2', 'version': 'WKT2_2019'})

    urls = []
    for c in crss:
        crs = pyproj.CRS.from_authority(auth_name=c["auth_name"], code=c["code"])
        for t in types:
            url = f'{t["path"]}/{c["auth_name"]}/{c["code"]}.txt'
            if not url in urls:
                urls.append(url)
            wtk_file = f'{dest_dir}/{url}'
            if not os.path.exists(os.path.dirname(wtk_file)):
                os.makedirs(os.path.dirname(wtk_file))

            try:
                output_axis_rule = True if crs.is_projected else None
                wkt = crs.to_wkt(version=t["version"], pretty=True, output_axis_rule=output_axis_rule)
            except:
                wkt = None
            if not wkt:
                type = str(c["type"]).replace('PJType.', '')
                wkt = (f'Error: {c["auth_name"]}:{c["code"]} cannot be written as {t["version"]}\n'
                        f' type: {type}\n'
                        f' name: {c["name"]}')
            with open(wtk_file, 'w') as fp:
                fp.write(wkt)
                fp.write('\n')
