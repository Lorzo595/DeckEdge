import base64
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
import httpx

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
from media_library import MediaLibrary, animated_controls, register_media, validate_image
from server import ButtonConfig


def png(color="red"):
    output = io.BytesIO()
    Image.new("RGB", (24, 24), color).save(output, "PNG")
    return output.getvalue()


def archive(files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as result:
        for name, data in files.items():
            result.writestr(name, data)
    return output.getvalue()


class MediaLibraryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "media"
        self.library = MediaLibrary(self.root)

    def test_sniffs_real_format_instead_of_extension(self):
        result = self.library.import_file(png(), "photo.gif")
        identifier = result["items"][0]["id"]
        self.assertTrue(identifier.endswith(".png"))
        self.assertEqual(self.library.path(identifier).read_bytes(), png())

    def test_animated_gif_is_kept_intact(self):
        name, raw = animated_controls()[1]
        result = self.library.import_file(raw, name)
        self.assertTrue(result["items"][0]["animated"])
        self.assertEqual(self.library.path(result["items"][0]["id"]).read_bytes(), raw)

    def test_svg_roundtrip_is_safe_and_has_stable_id(self):
        raw = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M0 0h24v24z"/></svg>'
        result = self.library.import_file(raw, "app.svg")
        identifier = result["items"][0]["id"]
        self.assertIn(b'#eeeeee', self.library.path(identifier).read_bytes())
        bundle = self.library.bundle([identifier])
        self.library.restore_bundle(bundle)
        self.assertEqual(len(self.library.listing()["items"]), 1)

    def test_active_svg_and_external_resources_are_rejected(self):
        for content in [b'<script>alert(1)</script>', b'<image href="http://localhost/"/>', b'<path fill="url(http://example.org)"/>', b'<path onload="alert(1)"/>']:
            with self.subTest(content=content), self.assertRaises(ValueError):
                validate_image(b'<svg xmlns="http://www.w3.org/2000/svg">' + content + b'</svg>')
        with self.assertRaises(ValueError):
            validate_image(b'<!DOCTYPE svg [<!ENTITY a SYSTEM "file:///secret">]><svg xmlns="http://www.w3.org/2000/svg">&a;</svg>')

    def test_invalid_pack_is_not_partially_installed(self):
        with self.assertRaises(ValueError):
            self.library.import_file(archive({"valid.png": png(), "bad.png": b"not an image"}), "bad.zip")
        self.assertFalse(self.root.exists())

    def test_zip_traversal_and_excessive_entries_are_rejected(self):
        for name in ["../escape.png", "/root.png", "C:\\escape.png", "folder\\..\\escape.png"]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.library.import_file(archive({name: png()}), "pack.zip")
        with self.assertRaises(ValueError):
            self.library.import_file(archive({f"{n}.png": png() for n in range(222)}), "pack.zip")

    def test_large_frames_and_invalid_images_are_rejected(self):
        output = io.BytesIO()
        Image.new("1", (4097, 1)).save(output, "PNG")
        for raw in [b"bad", b"", output.getvalue(), b"x" * (8*1024*1024+1)]:
            with self.assertRaises(ValueError):
                validate_image(raw)

    def test_pack_export_reimports_and_keeps_metadata(self):
        result = self.library.import_file(archive({"pack.json": json.dumps({"name":"Jeux", "source":"Lorzo595", "license":"MIT"}), "icons/game.png":png(), "readme.txt":"hello"}), "games.zip")
        exported = self.library.export_pack(result["pack"])
        second = MediaLibrary(self.root.parent / "second")
        restored = second.import_file(exported, "other.zip")
        self.assertEqual(restored["items"][0]["id"], result["items"][0]["id"])
        self.assertEqual(second.listing()["packs"][0]["name"], "Jeux")
        self.assertEqual(second.listing()["packs"][0]["license"], "MIT")

    def test_individual_imports_share_an_exportable_collection(self):
        self.library.import_file(png("red"), "red.png")
        self.library.import_file(png("blue"), "blue.png")
        self.assertEqual(len(self.library.listing()["packs"][0]["items"]), 2)
        self.assertEqual(len(zipfile.ZipFile(io.BytesIO(self.library.export_pack("personal"))).namelist()), 3)

    def test_duplicate_import_does_not_duplicate_bytes_or_items(self):
        self.library.import_file(png(), "one.png")
        self.library.import_file(png(), "two.png")
        self.assertEqual(len(self.library.listing()["items"]), 1)

    def test_remove_keeps_bytes_for_saved_keys_and_backups(self):
        identifier = self.library.import_file(png(), "photo.png")["items"][0]["id"]
        self.library.remove(identifier)
        self.assertEqual(self.library.listing()["items"], [])
        self.assertTrue(self.library.path(identifier).is_file())
        self.assertIn(identifier, self.library.bundle([identifier]))

    def test_profile_bundle_rejects_tampered_data_before_writing(self):
        identifier = "a" * 64 + ".png"
        with self.assertRaises(ValueError):
            self.library.restore_bundle({identifier: base64.b64encode(png()).decode()})
        self.assertFalse(self.root.exists())

    def test_model_only_allows_local_content_ids(self):
        for identifier in ["https://example.com/a.gif", "../../x.png", '<img src=x onerror=alert(1)>']:
            with self.assertRaises(ValueError):
                ButtonConfig(id="key", image=identifier)
        self.assertEqual(ButtonConfig(id="key").image, "")

    def client(self, host="127.0.0.1"):
        app = FastAPI()
        register_media(app, self.root)
        return TestClient(app, client=(host, 1234))

    def test_api_import_serve_restore_and_pack_export(self):
        with self.client() as client:
            response = client.post("/api/media/import?filename=picture.png", content=png())
            self.assertEqual(response.status_code, 200)
            identifier = response.json()["items"][0]["id"]
            response = client.get("/media/" + identifier)
            self.assertEqual(response.content, png())
            self.assertIn("sandbox", response.headers["content-security-policy"])
            self.assertEqual(client.get("/api/media/packs/personal/export").status_code, 200)
            bundle = client.post("/api/media/bundle", json=[identifier]).json()
            self.assertEqual(client.post("/api/media/restore", json=bundle).status_code, 200)

    def test_phone_cannot_manage_library(self):
        with self.client("192.168.1.55") as client:
            for method, url in [("get","/api/media"),("get","/api/media/catalog"),("post","/api/media/import"),("post","/api/media/catalog/pc-apps"),("post","/api/media/restore"),("post","/api/media/bundle"),("delete","/api/media/"+'a'*64+'.png')]:
                self.assertEqual(getattr(client,method)(url).status_code, 403)

    def test_real_server_requires_pairing_for_visual_files(self):
        from server import app, PHONE_KEY
        client = TestClient(app, base_url='http://192.168.1.50:5000', client=('192.168.1.55',1234))
        url='/media/'+'a'*64+'.png'
        self.assertEqual(client.get(url).status_code, 401)
        self.assertEqual(client.get(url+'?key='+PHONE_KEY).status_code, 404)
        self.assertEqual(client.get('/api/media').status_code, 403)

    def test_offline_gif_pack_and_unknown_pack(self):
        with self.client() as client:
            response = client.post("/api/media/catalog/animated-controls")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.json()["items"]), 3)
            self.assertTrue(all(item["animated"] for item in response.json()["items"]))
            exported = client.get('/api/media/packs/animated-controls/export').content
            self.assertEqual(client.post('/api/media/import?filename=animations.zip',content=exported).status_code, 200)
            self.assertEqual(len(client.get('/api/media').json()['packs']), 1)
            self.assertEqual(client.post("/api/media/catalog/no-such-pack").status_code, 404)

    def test_invalid_api_payloads_return_errors(self):
        with self.client() as client:
            for path, payload in [("/api/media/import",b"bad"),("/api/media/bundle",b"{}"),("/api/media/restore",b"[]"),("/api/media/restore",b"bad json")]:
                self.assertEqual(client.post(path,content=payload).status_code, 400)

    def test_failed_download_does_not_install_a_partial_pack(self):
        with self.client() as client, patch('media_library.httpx.AsyncClient', side_effect=httpx.ConnectError('offline')):
            self.assertEqual(client.post('/api/media/catalog/pc-apps').status_code, 502)
            self.assertEqual(self.library.listing()['items'], [])
