"""Local visual library: bounded imports, inert SVGs and shareable ZIP packs."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json
import re
import threading
import zipfile
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET

import httpx
from PIL import Image, ImageDraw
from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, Response
from network_access import is_local

MAX_FILE = 8 * 1024 * 1024
MAX_UPLOAD = 32 * 1024 * 1024
MAX_EXPANDED = 64 * 1024 * 1024
MAX_ITEMS = 200
ASSET_RE = re.compile(r"^[a-f0-9]{64}\.(png|jpg|webp|gif|svg|ico)$")
EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".ico"}
TITLES = {"discord":"Discord", "spotify":"Spotify", "firefoxbrowser":"Firefox", "vlcmediaplayer":"VLC", "obsstudio":"OBS Studio", "twitch":"Twitch", "steam":"Steam", "epicgames":"Epic Games", "gogdotcom":"GOG", "itchdotio":"itch.io", "ubisoft":"Ubisoft", "ea":"EA"}
CATALOG = [
    {"id": "pc-apps", "name": "Applications PC", "description": "Discord, Spotify, Firefox, VLC, OBS Studio et Twitch.",
     "source": "https://simpleicons.org", "license": "CC0-1.0 · marques de leurs propriétaires",
     "icons": ["discord", "spotify", "firefoxbrowser", "vlcmediaplayer", "obsstudio", "twitch"]},
    {"id": "gaming", "name": "Jeux et plateformes", "description": "Steam, Epic Games, GOG, itch.io, Ubisoft et EA.",
     "source": "https://simpleicons.org", "license": "CC0-1.0 · marques de leurs propriétaires",
     "icons": ["steam", "epicgames", "gogdotcom", "itchdotio", "ubisoft", "ea"]},
    {"id": "animated-controls", "name": "Commandes animées", "description": "GIF Lecture, Enregistrement et Chargement. Créés pour DeckEdge, disponibles hors ligne.",
     "source": "DeckEdge", "license": "MIT", "icons": []},
]


def validate_image(raw: bytes) -> tuple[bytes, str, bool]:
    if not raw or len(raw) > MAX_FILE:
        raise ValueError("Chaque visuel doit peser entre 1 octet et 8 Mo.")
    if raw.lstrip().startswith((b"<", b"\xef\xbb\xbf<")):
        if len(raw) > 256 * 1024 or re.search(br"<!|<\?", raw.replace(b'<?xml version="1.0" encoding="UTF-8"?>', b""), re.I):
            raise ValueError("SVG non pris en charge : déclaration ou contenu actif.")
        root = ET.fromstring(raw)
        tags = {"svg", "g", "path", "circle", "rect", "line", "polyline", "polygon", "ellipse", "title", "desc"}
        attrs = {"viewBox", "width", "height", "fill", "stroke", "stroke-width", "fill-rule", "clip-rule", "d", "points", "cx", "cy", "r", "rx", "ry", "x", "y", "x1", "x2", "y1", "y2", "transform", "opacity", "role"}
        if root.tag != "{http://www.w3.org/2000/svg}svg":
            raise ValueError("SVG invalide.")
        for node in root.iter():
            if node.tag.removeprefix("{http://www.w3.org/2000/svg}") not in tags:
                raise ValueError("SVG non pris en charge : élément actif ou externe.")
            for key, value in node.attrib.items():
                if key not in attrs or re.search(r"url\s*\(|javascript:|https?:|data:", value, re.I):
                    raise ValueError("SVG non pris en charge : attribut actif ou externe.")
        # White is legible on dark keys; explicit colours from imported artwork stay intact.
        root.attrib.setdefault("fill", "#eeeeee")
        return ET.tostring(root, encoding="utf-8"), "svg", False
    try:
        with Image.open(io.BytesIO(raw)) as image:
            formats = {"PNG": "png", "JPEG": "jpg", "WEBP": "webp", "GIF": "gif", "ICO": "ico"}
            extension = formats.get(image.format)
            frames = getattr(image, "n_frames", 1)
            width, height = image.size
            if not extension or max(width, height) > 4096 or width * height * frames > 64_000_000 or frames > 300:
                raise ValueError("Visuel trop grand : 4096 px, 300 images et 64 millions de pixels cumulés maximum.")
            for index in range(frames):
                image.seek(index)
                image.load()
            return raw, extension, frames > 1
    except (OSError, EOFError, Image.DecompressionBombError) as exc:
        raise ValueError("Image illisible ou format non pris en charge.") from exc


class MediaLibrary:
    def __init__(self, directory: Path):
        self.directory = directory
        self.lock = threading.RLock()

    def _index(self):
        path = self.directory / "library.json"
        return json.loads(path.read_text("utf-8")) if path.exists() else {"items": [], "packs": []}

    def listing(self):
        with self.lock:
            return self._index()

    def path(self, identifier):
        if not ASSET_RE.fullmatch(identifier):
            raise ValueError("Identifiant de visuel invalide.")
        return self.directory / identifier

    def install(self, entries, name, *, source="Import local", license="", pack_id=None, expected_ids=None):
        if not 1 <= len(entries) <= MAX_ITEMS or sum(len(raw) for _, raw in entries) > MAX_EXPANDED:
            raise ValueError("Un pack accepte 1 à 200 visuels et 64 Mo décompressés maximum.")
        prepared = []
        for filename, raw in entries:
            data, extension, animated = validate_image(raw)
            identifier = hashlib.sha256(data).hexdigest() + "." + extension
            if expected_ids is not None and identifier != expected_ids[len(prepared)]:
                raise ValueError("Un visuel du profil ne correspond pas à son identifiant.")
            prepared.append((identifier, data, {"id": identifier, "name": Path(filename).stem[:80], "animated": animated}))
        with self.lock:
            index = self._index()
            self.directory.mkdir(parents=True, exist_ok=True)
            if len({item["id"] for item in index["items"]} | {item[0] for item in prepared}) > 2000:
                raise ValueError("La bibliothèque est limitée à 2 000 visuels.")
            if pack_id is None:
                contents = {item[0] for item in prepared}
                pack_id = next((pack["id"] for pack in index["packs"] if pack["name"] == name[:80] and pack["source"] == source[:300] and pack["license"] == license[:200] and set(pack["items"]) == contents), None)
            pack_id = pack_id or hashlib.sha256((name + "\n" + "\n".join(item[0] for item in prepared)).encode()).hexdigest()[:20]
            previous = next((pack["items"] for pack in index["packs"] if pack["id"] == pack_id), [])
            known = {item["id"] for item in index["items"]}
            for identifier, data, metadata in prepared:
                target = self.path(identifier)
                if not target.exists():
                    temporary = self.directory / (identifier + ".tmp")
                    temporary.write_bytes(data)
                    temporary.replace(target)
                if identifier not in known:
                    metadata["pack"] = pack_id
                    index["items"].append(metadata)
                    known.add(identifier)
            index["packs"] = [pack for pack in index["packs"] if pack["id"] != pack_id]
            index["packs"].append({"id": pack_id, "name": name[:80], "source": source[:300], "license": license[:200], "items": list(dict.fromkeys(previous + [item[0] for item in prepared]))})
            self._save(index)
            return {"items": [item[2] for item in prepared], "pack": pack_id}

    def _save(self, index):
        temporary = self.directory / "library.json.tmp"
        temporary.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        temporary.replace(self.directory / "library.json")

    def import_file(self, raw, filename):
        if filename.lower().endswith((".zip", ".deckedge-pack")):
            try:
                with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                    files = archive.infolist()
                    if len(files) > MAX_ITEMS + 20 or sum(item.file_size for item in files) > MAX_EXPANDED:
                        raise ValueError("Pack trop volumineux : 200 visuels et 64 Mo maximum.")
                    for item in files:
                        path = PurePosixPath(item.filename.replace("\\", "/"))
                        if path.is_absolute() or ".." in path.parts or ":" in item.filename or item.flag_bits & 1:
                            raise ValueError("Chemin ou archive chiffrée non pris en charge.")
                    metadata = {}
                    if "pack.json" in archive.namelist():
                        if archive.getinfo("pack.json").file_size > 64 * 1024:
                            raise ValueError("Métadonnées du pack trop grandes.")
                        metadata = json.loads(archive.read("pack.json"))
                        if not isinstance(metadata, dict):
                            raise ValueError("Métadonnées du pack invalides.")
                    entries = [(item.filename, archive.read(item)) for item in files if not item.is_dir() and PurePosixPath(item.filename).suffix.lower() in EXTENSIONS]
                    return self.install(entries, str(metadata.get("name") or Path(filename).stem), source=str(metadata.get("source", "Import local")), license=str(metadata.get("license", "")))
            except (zipfile.BadZipFile, RuntimeError, KeyError) as exc:
                raise ValueError("Archive ZIP illisible.") from exc
        return self.install([(filename, raw)], "Mes imports", pack_id="personal")

    def bundle(self, identifiers):
        if len(identifiers) > MAX_ITEMS:
            raise ValueError("Un export accepte 200 visuels maximum.")
        result = {}
        size = 0
        for identifier in dict.fromkeys(identifiers):
            path = self.path(identifier)
            if not path.is_file():
                raise ValueError("Un visuel utilisé est introuvable. Réimportez son pack avant d’exporter.")
            raw = path.read_bytes()
            size += len(raw)
            if size > 20 * 1024 * 1024:
                raise ValueError("L’export est limité à 20 Mo de visuels. Exportez les packs séparément.")
            result[identifier] = base64.b64encode(raw).decode("ascii")
        return result

    def restore_bundle(self, bundle):
        if not isinstance(bundle, dict) or len(bundle) > MAX_ITEMS:
            raise ValueError("Visuels du profil invalides.")
        entries, ids = [], []
        for identifier, encoded in bundle.items():
            self.path(identifier)
            if not isinstance(encoded, str) or len(encoded) > MAX_FILE * 4 // 3 + 8:
                raise ValueError("Visuel du profil trop volumineux.")
            entries.append((identifier, base64.b64decode(encoded, validate=True)))
            ids.append(identifier)
        if entries:
            self.install(entries, "Profils importés", expected_ids=ids)

    def remove(self, identifier):
        self.path(identifier)
        with self.lock:
            index = self._index()
            index["items"] = [item for item in index["items"] if item["id"] != identifier]
            for pack in index["packs"]:
                pack["items"] = [item for item in pack["items"] if item != identifier]
            self._save(index)
        # Keep file bytes: saved keys, undo history and backups may still use them.

    def export_pack(self, pack_id):
        with self.lock:
            index = self._index()
            pack = next((pack for pack in index["packs"] if pack["id"] == pack_id), None)
            if not pack:
                raise ValueError("Pack introuvable.")
            bundle = self.bundle(pack["items"])
            output = io.BytesIO()
            with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("pack.json", json.dumps({"format": "deckedge-pack", "version": 1, **pack}, ensure_ascii=False))
                names = {item["id"]: item["name"] for item in index["items"]}
                for identifier, encoded in bundle.items():
                    name = re.sub(r"[^\w .-]", "_", names.get(identifier, identifier))[:80]
                    archive.writestr(f"icons/{identifier[:8]}-{name}.{identifier.rsplit('.',1)[1]}", base64.b64decode(encoded))
            return output.getvalue()


def animated_controls():
    entries = []
    for name in ("Lecture", "Enregistrement", "Chargement"):
        frames = []
        for frame in range(16):
            image = Image.new("RGB", (96, 96), "#292929")
            draw = ImageDraw.Draw(image)
            if name == "Lecture":
                draw.polygon([(34, 22), (34, 74), (75, 48)], fill=(100, 170 + frame * 4, 220))
            elif name == "Enregistrement":
                radius = 20 + abs(8 - frame)
                draw.ellipse((48-radius, 48-radius, 48+radius, 48+radius), fill="#e36b6b")
            else:
                draw.arc((20, 20, 76, 76), frame * 22.5, frame * 22.5 + 260, fill="#83b5d5", width=7)
            frames.append(image)
        buffer = io.BytesIO()
        frames[0].save(buffer, format="GIF", save_all=True, append_images=frames[1:], duration=80, loop=0)
        entries.append((name + ".gif", buffer.getvalue()))
    return entries


async def bounded_body(request):
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_UPLOAD:
            raise HTTPException(413, "Import limité à 32 Mo.")
    return bytes(body)


def register_media(app, directory):
    library = MediaLibrary(directory)

    def local(request):
        if not request.client or not is_local(request.client.host):
            raise HTTPException(403, "La bibliothèque se gère depuis le PC.")

    async def operation(function, *args, **kwargs):
        try:
            return await asyncio.to_thread(function, *args, **kwargs)
        except (ValueError, ET.ParseError, OSError) as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/api/media")
    async def listing(request: Request):
        local(request)
        return await operation(library.listing)

    @app.get("/api/media/catalog")
    async def catalog(request: Request):
        local(request)
        return {"packs": [{**item, "count": len(item["icons"]) or 3} for item in CATALOG]}

    @app.post("/api/media/import")
    async def import_media(request: Request, filename: str = "image.png"):
        local(request)
        return await operation(library.import_file, await bounded_body(request), filename[:200])

    @app.post("/api/media/catalog/{pack_id}")
    async def install_catalog(pack_id: str, request: Request):
        local(request)
        pack = next((item for item in CATALOG if item["id"] == pack_id), None)
        if not pack:
            raise HTTPException(404, "Pack introuvable.")
        if pack_id == "animated-controls":
            entries = await asyncio.to_thread(animated_controls)
        else:
            entries = []
            try:
                async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
                    for icon in pack["icons"]:
                        # No user-supplied URL: downloads cannot target local network services.
                        async with client.stream("GET", f"https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/{icon}.svg") as response:
                            response.raise_for_status()
                            raw = bytearray()
                            async for chunk in response.aiter_bytes():
                                raw.extend(chunk)
                                if len(raw) > 256 * 1024:
                                    raise ValueError("Icône distante trop volumineuse.")
                            entries.append((TITLES[icon] + ".svg", bytes(raw)))
            except (httpx.HTTPError, ValueError) as exc:
                raise HTTPException(502, "Téléchargement impossible. Vérifiez la connexion puis réessayez.") from exc
        return await operation(library.install, entries, pack["name"], source=pack["source"], license=pack["license"], pack_id=pack_id)

    @app.post("/api/media/bundle")
    async def bundle_media(request: Request):
        local(request)
        try:
            payload = json.loads(await bounded_body(request))
            if not isinstance(payload, list) or not all(isinstance(item, str) for item in payload):
                raise ValueError("Liste de visuels invalide.")
            return await operation(library.bundle, payload)
        except (ValueError, TypeError) as exc:
            raise HTTPException(400, "Liste de visuels invalide.") from exc

    @app.post("/api/media/restore")
    async def restore_media(request: Request):
        local(request)
        try:
            payload = json.loads(await bounded_body(request))
        except ValueError as exc:
            raise HTTPException(400, "Visuels invalides.") from exc
        await operation(library.restore_bundle, payload)
        return {"status": "ok"}

    @app.delete("/api/media/{identifier}")
    async def remove_media(identifier: str, request: Request):
        local(request)
        await operation(library.remove, identifier)
        return {"status": "ok"}

    @app.get("/api/media/packs/{pack_id}/export")
    async def export_pack(pack_id: str, request: Request):
        local(request)
        return Response(await operation(library.export_pack, pack_id), media_type="application/zip", headers={"Content-Disposition": 'attachment; filename="deckedge-pack.zip"'})

    @app.get("/media/{identifier}")
    async def media_file(identifier: str):
        try:
            path = library.path(identifier)
        except ValueError as exc:
            raise HTTPException(404) from exc
        if not path.is_file():
            raise HTTPException(404)
        return FileResponse(path, headers={"Cache-Control": "private, max-age=31536000, immutable", "Content-Security-Policy": "default-src 'none'; sandbox"})

    return library
