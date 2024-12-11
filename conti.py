from core import Core
from ctrl_scene import div_scene

import re
import shortuuid
import json
import urllib
import base64

from openpyxl import Workbook
from openpyxl.drawing.image import Image
from openpyxl.styles import Alignment

from io import BytesIO

class Conti( Core ):
    def draw_conti( self, scenario, scenario_idx, div_num ):
        load_div_scene = self.db.load_div_scene(scenario_idx)
        if not load_div_scene:
            div_scenes = div_scene( self.chain, scenario, div_num )
            for d in div_scenes:
                self.db.insert_div_scene( d[0], d[1], scenario_idx)
        else:
            div_scenes = []
            for s in load_div_scene:
                div_scenes.append([s[1], s[2]])

        sd_server_url = 'http://10.0.80.181:7861'

        prompt = "이 시스템은 유능한 시나리오 축약 전문가입니다."
        prompt += "다음에 오는 내용을 영어로 한 문장으로 압축해서 stable diffusion 프롬프트를 작성해주세요."
        prompt += "다른 건 아무것도 출력하지 말고 오직 영어 프롬프트만 출력해주세요."
        prompt += "내용 : {scene}"

        for scene in div_scenes:
            chain = self.chain(prompt)
            response = chain.invoke( {'scene':scene[1]} )

            if scene[0] == 1:
                seed = -1
            
            payload = {
                "prompt": f"cconti, sketch of {response}, mono, gray <lora:cconti:1>",
                "negative_prompt": "",
                "seed": seed,
                "steps": 20,
                "width": 1024,
                "height": 512,
                "cfg_scale": 7,
                "sampler_name": "Euler a",
                "n_iter": 1,
                "batch_size": 1,
            }

            data = json.dumps(payload).encode('utf-8')
            request = urllib.request.Request(
                f'{sd_server_url}/sdapi/v1/txt2img',
                headers={'Content-Type': 'application/json'},
                data=data,
            )
            image_url = urllib.request.urlopen(request)
            image = json.loads(image_url.read().decode('utf-8'))

            img_uid = str(shortuuid.uuid())
            img_path = f'./tmp/conti/scene{scene[0]}_{ img_uid }.png'
            with open(img_path, "wb") as file:
                file.write(base64.b64decode(image.get('images')[0]))
            
            seed_info = json.loads(image.get('info'))
            seed = seed_info['seed']

            div_idx = self.db.search_div_idx( scene[0], scenario_idx )
            self.db.insert_conti( img_path, div_idx )

    def save_conti( self, scenario_idx ):
        wb = Workbook()
        ws = wb.active

        scenes = self.db.load_div_scene( scenario_idx )

        for scene_data in scenes:
            scene = scene_data[2]
            img_path = self.db.load_conti( scene_data[0] )
            row = scene_data[1]

            cell = ws.cell( row = row + 1, column = 1 , value = scene )
            cell.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')

            with open(img_path, 'rb') as img_file:
                img = Image(BytesIO(img_file.read()))
            img.height = 320
            img.width = 320
            ws.add_image( img, 'B{}'.format( row + 1 ) )
            ws.row_dimensions[ row+1 ].height = 320
            ws.column_dimensions[ 'A' ].width = 90

        conti_path = './tmp/conti.xlsx'
        wb.save(  conti_path )
        return conti_path
