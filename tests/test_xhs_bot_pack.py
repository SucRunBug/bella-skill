"""Check the real archive boundary and the approval gate with isolated fixtures."""
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile
import zlib

SCRIPT=Path(__file__).resolve().parents[1]/'skills/media/xhs-bot-content-pack/scripts/pack_delivery.py'


def portrait_png():
    def chunk(kind,body):
        return struct.pack('>I',len(body))+kind+body+struct.pack('>I',zlib.crc32(kind+body)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',3,4,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+b'\xff'*9)*4))+chunk(b'IEND',b'')


class BotPackTests(unittest.TestCase):
    def fixture(self,root):
        files={key:key+'.md' for key in ['plan','copy','prompts','sources','research']}
        files.update(workbook='选品表.xlsx',ip='assets/ip.png')
        for name in files.values():
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'fixture')
        for name in ['cover.png','interior.png']:(root/name).write_bytes(portrait_png())
        d={'topic':'Fixture','publish_date':'2026-11-07','plan_version':'v1','stage':'complete','mode':'products','item_count':1,'per_page':1,'title':'求分享','title_candidates':['求分享','求避雷','一人一个','省点钱','囤什么'],'cover_question':'用什么','caption':'正文','first_comment':'报个名字','viral_logic':'明确场景降低回答门槛','seasonal_hook':'开学季','tags':['#'+str(i) for i in range(6)],'visual':{k:'fixture' for k in ['palette','layout','typography','ip','decorations']},'approval':{'confirmed':True,'plan_version':'v1','user_confirmation':'Fixture: user confirmed v1'},'constraints':{'unit_budget':20},'items':[{'id':'P1','name':'Fixture product','page':1,'spec':'1份','price':5,'price_basis':'single_purchasable_unit','buy_url':'https://example.com/product','source_urls':['https://example.com/product']}],'files':files,'images':{'cover':'cover.png','interiors':['interior.png']}}
        manifest=root/'内容数据.json';manifest.write_text(json.dumps(d,ensure_ascii=False))
        return manifest,d

    def run_pack(self,root,mutate=None):
        manifest,data=self.fixture(root)
        if mutate:mutate(data)
        manifest.write_text(json.dumps(data,ensure_ascii=False))
        (root/'unlisted-private.txt').write_text('not a deliverable')
        result=subprocess.run([sys.executable,str(SCRIPT),'package',str(manifest),'--output',str(root/'pack.zip')],capture_output=True,text=True)
        return result,root/'pack.zip'

    def test_package_includes_workbook_and_declared_assets_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            result,archive=self.run_pack(Path(tmp))
            self.assertEqual(result.returncode,0,result.stderr)
            with ZipFile(archive) as z:
                self.assertIn('选品表.xlsx',z.namelist())
                self.assertIn('assets/ip.png',z.namelist())
                self.assertNotIn('unlisted-private.txt',z.namelist())
                self.assertIsNone(z.testzip())

    def test_missing_declared_workbook_rejects_complete_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            result,archive=self.run_pack(Path(tmp),lambda d:d['files'].update(workbook='missing.xlsx'))
            self.assertNotEqual(result.returncode,0)
            self.assertFalse(archive.exists())

    def test_extra_file_cannot_escape_task_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            result,archive=self.run_pack(Path(tmp),lambda d:d['files'].update(ip='../outside.png'))
            self.assertNotEqual(result.returncode,0)
            self.assertIn('escapes task directory',result.stderr)
            self.assertFalse(archive.exists())

    def test_unconfirmed_visual_cannot_be_packaged_as_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            result,archive=self.run_pack(Path(tmp),lambda d:d['approval'].update(confirmed=False))
            self.assertNotEqual(result.returncode,0)
            self.assertFalse(archive.exists())

    def test_older_approval_does_not_authorize_new_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            result,archive=self.run_pack(Path(tmp),lambda d:d.update(plan_version='v2'))
            self.assertNotEqual(result.returncode,0)
            self.assertFalse(archive.exists())


if __name__=='__main__':unittest.main()
