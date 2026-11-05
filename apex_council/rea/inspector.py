"""Binary and artifact inspection engine for REA.
Detects binary formats (ELF, PE, ZIP, PYC, TEXT) and parses headers/metadata.
100% pure Python standard library implementation with zero external dependencies.
"""

from __future__ import annotations

import ast
import hashlib
import io
import os
import struct
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .models import ArtifactInspection

# Known format magic signatures
MAGIC_ELF = b"\x7fELF"
MAGIC_PE_DOS = b"MZ"
MAGIC_PE_NT = b"PE\x00\x00"
MAGIC_ZIP_LOCAL = b"PK\x03\x04"
MAGIC_ZIP_EMPTY = b"PK\x05\x06"
MAGIC_ZIP_SPANNED = b"PK\x07\x08"

# ELF Machine mappings
ELF_MACHINES = {
    0x03: "x86",
    0x3E: "x86-64 / AMD64",
    0x28: "ARM",
    0xB7: "AArch64",
    0xF3: "RISC-V",
    0x08: "MIPS",
    0x14: "PowerPC",
    0x2A: "SuperH",
    0x32: "IA-64",
}

# ELF Type mappings
ELF_TYPES = {
    0: "ET_NONE",
    1: "ET_REL (Relocatable)",
    2: "ET_EXEC (Executable)",
    3: "ET_DYN (Shared object / PIE)",
    4: "ET_CORE (Core dump)",
}

# PE Machine mappings
PE_MACHINES = {
    0x014C: "i386 (32-bit)",
    0x8664: "AMD64 / x86-64 (64-bit)",
    0x01C0: "ARM (Thumb)",
    0xAA64: "ARM64 (64-bit)",
    0x0200: "Intel Itanium",
}

# Common source extensions mapped to language
SOURCE_EXTENSIONS = {
    ".py": "python",
    ".c": "c",
    ".h": "c_header",
    ".cpp": "cpp",
    ".hpp": "cpp_header",
    ".rs": "rust",
    ".go": "go",
    ".js": "javascript",
    ".ts": "typescript",
    ".java": "java",
    ".sh": "shell",
    ".bat": "batch",
    ".ps1": "powershell",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".xml": "xml",
    ".html": "html",
    ".md": "markdown",
    ".txt": "text",
}


def detect_format(data: bytes, file_path: Optional[str] = None) -> str:
    """Detect artifact format from leading bytes and path cues."""
    if len(data) >= 4 and data[:4] == MAGIC_ELF:
        return "ELF"

    if len(data) >= 2 and data[:2] == MAGIC_PE_DOS:
        if len(data) >= 0x40:
            e_lfanew = struct.unpack("<I", data[0x3C:0x40])[0]
            if 0 < e_lfanew <= len(data) - 4 and data[e_lfanew:e_lfanew + 4] == MAGIC_PE_NT:
                return "PE"
        if file_path and file_path.lower().endswith((".exe", ".dll", ".sys", ".efi")):
            return "PE"

    if len(data) >= 4 and data[:4] in (MAGIC_ZIP_LOCAL, MAGIC_ZIP_EMPTY, MAGIC_ZIP_SPANNED):
        return "ZIP"

    # Python bytecode check
    if file_path and file_path.lower().endswith(".pyc"):
        return "PYC"
    if len(data) >= 4 and (data[2:4] == b"\r\n" or data[1:4] == b"\r\r\n" or data[0:2] == b"\xa7\r"):
        return "PYC"

    # Plain text / Source check: check for lack of null bytes in first 1024 bytes
    sample = data[:1024]
    if b"\x00" not in sample:
        try:
            sample.decode("utf-8")
            return "TEXT"
        except UnicodeDecodeError:
            try:
                sample.decode("latin-1")
                return "TEXT"
            except Exception:
                pass

    if file_path:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in SOURCE_EXTENSIONS:
            return "TEXT"

    return "UNKNOWN"


def parse_elf_header(data: bytes) -> Dict[str, Any]:
    """Parse ELF binary header and section headers."""
    meta: Dict[str, Any] = {"format_type": "ELF"}
    if len(data) < 52:
        meta["error"] = "ELF file truncated (header < 52 bytes)"
        return meta

    ei_class = data[4]  # 1 = 32-bit, 2 = 64-bit
    ei_data = data[5]   # 1 = little-endian, 2 = big-endian
    endian = "<" if ei_data == 1 else ">"

    meta["bitness"] = 64 if ei_class == 2 else 32
    meta["endianness"] = "little-endian" if ei_data == 1 else "big-endian"
    meta["os_abi"] = data[7]

    try:
        if ei_class == 2:  # 64-bit ELF
            if len(data) < 64:
                meta["error"] = "ELF64 truncated (header < 64 bytes)"
                return meta
            (
                e_type, e_machine, e_version, e_entry,
                e_phoff, e_shoff, e_flags, e_ehsize,
                e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx
            ) = struct.unpack(f"{endian}HHIQQQIHHHHHH", data[16:64])
        else:  # 32-bit ELF
            (
                e_type, e_machine, e_version, e_entry,
                e_phoff, e_shoff, e_flags, e_ehsize,
                e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx
            ) = struct.unpack(f"{endian}HHIIIIIHHHHHH", data[16:52])

        meta["elf_type"] = ELF_TYPES.get(e_type, f"ET_UNKNOWN ({e_type})")
        meta["machine"] = ELF_MACHINES.get(e_machine, f"Unknown (0x{e_machine:04x})")
        meta["entry_point"] = hex(e_entry)
        meta["program_headers_count"] = e_phnum
        meta["section_headers_count"] = e_shnum
        meta["section_names"] = []

        # Parse section headers if present and intact
        sections = []
        if e_shoff > 0 and e_shnum > 0 and e_shentsize >= 40:
            sh_data_offset = e_shoff
            # Extract raw section descriptors
            raw_sections = []
            for i in range(min(e_shnum, 128)):  # limit to 128 sections
                sec_off = sh_data_offset + i * e_shentsize
                if sec_off + e_shentsize > len(data):
                    break
                if ei_class == 2 and e_shentsize >= 64:
                    sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size, _, _, _, _ = struct.unpack(
                        f"{endian}IIQQQQIIQQ", data[sec_off:sec_off + 64]
                    )
                else:
                    sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size, _, _, _, _ = struct.unpack(
                        f"{endian}IIIIIIIIII", data[sec_off:sec_off + 40]
                    )
                raw_sections.append({
                    "name_offset": sh_name,
                    "type": sh_type,
                    "flags": sh_flags,
                    "addr": hex(sh_addr),
                    "offset": sh_offset,
                    "size": sh_size,
                })

            # Read section names from string table if within bounds
            strtab = b""
            if 0 <= e_shstrndx < len(raw_sections):
                strtab_desc = raw_sections[e_shstrndx]
                st_off = strtab_desc["offset"]
                st_sz = strtab_desc["size"]
                if st_off + st_sz <= len(data):
                    strtab = data[st_off:st_off + st_sz]

            sec_names = []
            for rsec in raw_sections:
                name = ""
                no = rsec["name_offset"]
                if strtab and no < len(strtab):
                    null_idx = strtab.find(b"\x00", no)
                    if null_idx != -1:
                        name = strtab[no:null_idx].decode("latin-1", errors="replace")
                if not name:
                    name = f"sec_{len(sec_names)}"
                sec_names.append(name)
                sections.append({
                    "name": name,
                    "type": rsec["type"],
                    "addr": rsec["addr"],
                    "size": rsec["size"],
                })

            meta["section_names"] = sec_names
            meta["sections"] = sections
    except Exception as e:
        meta["parse_warning"] = f"Failed to fully parse ELF details: {e}"

    return meta


def parse_pe_header(data: bytes) -> Dict[str, Any]:
    """Parse PE DOS/COFF/Optional and section headers."""
    meta: Dict[str, Any] = {"format_type": "PE"}
    if len(data) < 0x40:
        meta["error"] = "PE file truncated (data < 64 bytes)"
        return meta

    try:
        e_lfanew = struct.unpack("<I", data[0x3C:0x40])[0]
        meta["e_lfanew"] = e_lfanew

        if e_lfanew + 24 > len(data):
            meta["warning"] = "PE signature/COFF header extends beyond file boundary"
            return meta

        if data[e_lfanew:e_lfanew + 4] != MAGIC_PE_NT:
            meta["warning"] = "PE signature missing at e_lfanew (possible pure DOS binary)"
            return meta

        # COFF Header (20 bytes)
        coff_offset = e_lfanew + 4
        machine, n_sections, timedatestamp, p_symbols, n_symbols, opt_hdr_size, characteristics = struct.unpack(
            "<HHIIIHH", data[coff_offset:coff_offset + 20]
        )

        meta["machine"] = PE_MACHINES.get(machine, f"Unknown (0x{machine:04x})")
        meta["section_count"] = n_sections
        meta["timedatestamp"] = timedatestamp
        meta["characteristics"] = characteristics
        meta["is_dll"] = bool(characteristics & 0x2000)

        # Optional Header
        opt_offset = coff_offset + 20
        if opt_hdr_size >= 2 and opt_offset + opt_hdr_size <= len(data):
            opt_magic = struct.unpack("<H", data[opt_offset:opt_offset + 2])[0]
            is_pe32_plus = (opt_magic == 0x020B)
            meta["pe_format"] = "PE32+ (64-bit)" if is_pe32_plus else "PE32 (32-bit)"

            if opt_hdr_size >= 20:
                entry_point = struct.unpack("<I", data[opt_offset + 16:opt_offset + 20])[0]
                meta["entry_point"] = hex(entry_point)

            if is_pe32_plus and opt_hdr_size >= 32:
                image_base = struct.unpack("<Q", data[opt_offset + 24:opt_offset + 32])[0]
                meta["image_base"] = hex(image_base)
            elif not is_pe32_plus and opt_hdr_size >= 28:
                image_base = struct.unpack("<I", data[opt_offset + 28:opt_offset + 32])[0]
                meta["image_base"] = hex(image_base)

            # Subsystem
            if opt_hdr_size >= 70:
                subsystem = struct.unpack("<H", data[opt_offset + 68:opt_offset + 70])[0]
                meta["subsystem"] = "Windows GUI" if subsystem == 2 else "Windows Console" if subsystem == 3 else f"Other ({subsystem})"

        # Section Headers (40 bytes each)
        sec_offset = opt_offset + opt_hdr_size
        sections = []
        section_names = []
        for i in range(min(n_sections, 96)):
            curr_sec = sec_offset + i * 40
            if curr_sec + 40 > len(data):
                break
            raw_name, virt_size, virt_addr, raw_size, raw_ptr, _, _, _, _, charact = struct.unpack(
                "<8sIIIIIIHHI", data[curr_sec:curr_sec + 40]
            )
            name = raw_name.rstrip(b"\x00").decode("latin-1", errors="replace")
            section_names.append(name)
            sections.append({
                "name": name,
                "virtual_address": hex(virt_addr),
                "virtual_size": virt_size,
                "raw_size": raw_size,
                "characteristics": hex(charact),
            })

        meta["section_names"] = section_names
        meta["sections"] = sections
    except Exception as e:
        meta["parse_warning"] = f"Failed to parse PE sections: {e}"

    return meta


def parse_zip_metadata(data: bytes, file_path: Optional[str] = None) -> Dict[str, Any]:
    """Parse ZIP / JAR / APK / Wheel archive metadata."""
    meta: Dict[str, Any] = {"format_type": "ZIP"}
    try:
        buf = io.BytesIO(data)
        with zipfile.ZipFile(buf, "r") as zf:
            infolist = zf.infolist()
            meta["entry_count"] = len(infolist)
            total_uncompressed = sum(info.file_size for info in infolist)
            total_compressed = sum(info.compress_size for info in infolist)
            meta["total_uncompressed_bytes"] = total_uncompressed
            meta["total_compressed_bytes"] = total_compressed
            if total_uncompressed > 0:
                meta["compression_ratio"] = round(total_compressed / total_uncompressed, 3)

            filenames = [info.filename for info in infolist]
            meta["sample_entries"] = filenames[:25]

            # Specialized archive identification
            if "META-INF/MANIFEST.MF" in filenames:
                meta["archive_subtype"] = "JAR"
            elif "AndroidManifest.xml" in filenames:
                meta["archive_subtype"] = "APK"
            elif any(f.endswith(".dist-info/METADATA") for f in filenames):
                meta["archive_subtype"] = "Python Wheel"
            elif "[Content_Types].xml" in filenames:
                meta["archive_subtype"] = "Office Open XML (DOCX/XLSX)"
            else:
                meta["archive_subtype"] = "Standard ZIP"
    except Exception as e:
        meta["error"] = f"Invalid or corrupted ZIP archive: {e}"

    return meta


def parse_pyc_metadata(data: bytes) -> Dict[str, Any]:
    """Parse Python bytecode (.pyc) header and marshalled code object."""
    meta: Dict[str, Any] = {"format_type": "PYC"}
    if len(data) < 16:
        meta["error"] = "PYC file truncated (< 16 bytes)"
        return meta

    try:
        import marshal
        magic = data[:4]
        meta["magic_bytes"] = magic.hex()

        flags = struct.unpack("<I", data[4:8])[0]
        meta["flags"] = flags
        meta["is_hash_based"] = bool(flags & 1)

        if not meta["is_hash_based"]:
            timestamp = struct.unpack("<I", data[8:12])[0]
            size = struct.unpack("<I", data[12:16])[0]
            meta["source_timestamp"] = timestamp
            meta["source_size_bytes"] = size

        # Unmarshal code object
        code_data = data[16:]
        code_obj = marshal.loads(code_data)
        meta["code_name"] = getattr(code_obj, "co_name", "<unknown>")
        meta["code_filename"] = getattr(code_obj, "co_filename", "<unknown>")
        meta["arg_count"] = getattr(code_obj, "co_argcount", 0)
        meta["names"] = list(getattr(code_obj, "co_names", ()))
        meta["var_names"] = list(getattr(code_obj, "co_varnames", ()))
        meta["const_count"] = len(getattr(code_obj, "co_consts", ()))
        meta["stack_size"] = getattr(code_obj, "co_stacksize", 0)
    except Exception as e:
        meta["unmarshal_warning"] = f"Failed to unmarshal Python code object: {e}"

    return meta


def parse_text_metadata(data: bytes, file_path: Optional[str] = None) -> Dict[str, Any]:
    """Parse plain text or source code metadata."""
    meta: Dict[str, Any] = {"format_type": "TEXT"}
    try:
        text = data.decode("utf-8")
        meta["encoding"] = "utf-8"
    except UnicodeDecodeError:
        text = data.decode("latin-1", errors="replace")
        meta["encoding"] = "latin-1"

    lines = text.splitlines()
    meta["line_count"] = len(lines)
    meta["non_empty_lines"] = sum(1 for line in lines if line.strip())
    meta["char_count"] = len(text)
    meta["max_line_length"] = max((len(l) for l in lines), default=0)

    # Detect language by extension or cues
    lang = "text"
    if file_path:
        ext = os.path.splitext(file_path)[1].lower()
        lang = SOURCE_EXTENSIONS.get(ext, "text")
    meta["language"] = lang

    # If Python, extract AST definitions
    if lang == "python":
        try:
            tree = ast.parse(text)
            funcs = [n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
            imports = []
            for n in ast.walk(tree):
                if isinstance(n, ast.Import):
                    imports.extend(alias.name for alias in n.names)
                elif isinstance(n, ast.ImportFrom):
                    mod = n.module or ""
                    for alias in n.names:
                        imports.append(f"{mod}.{alias.name}")

            meta["ast_functions"] = funcs
            meta["ast_classes"] = classes
            meta["ast_imports"] = sorted(set(imports))
        except Exception as e:
            meta["ast_parse_error"] = str(e)

    return meta


def inspect_artifact(target_path: Union[str, Path]) -> ArtifactInspection:
    """Main REA artifact inspector: detects format, computes digests & extracts metadata."""
    path_obj = Path(target_path)
    if not path_obj.exists():
        return ArtifactInspection(
            target_path=str(target_path),
            size_bytes=0,
            sha256="",
            format="UNKNOWN",
            is_binary=False,
            error=f"Artifact not found: {target_path}",
        )

    try:
        data = path_obj.read_bytes()
    except Exception as e:
        return ArtifactInspection(
            target_path=str(target_path),
            size_bytes=0,
            sha256="",
            format="UNKNOWN",
            is_binary=False,
            error=f"Failed to read artifact: {e}",
        )

    return inspect_bytes(data, filename=str(target_path))


def inspect_bytes(data: bytes, filename: str = "memory_buffer") -> ArtifactInspection:
    """Inspect raw in-memory byte buffer."""
    size_bytes = len(data)
    sha256_hash = hashlib.sha256(data).hexdigest()
    fmt = detect_format(data, file_path=filename)
    is_binary = fmt in ("ELF", "PE", "ZIP", "PYC", "UNKNOWN")

    metadata: Dict[str, Any] = {}
    mime_type = "application/octet-stream"

    if fmt == "ELF":
        mime_type = "application/x-executable"
        metadata = parse_elf_header(data)
    elif fmt == "PE":
        metadata = parse_pe_header(data)
        mime_type = "application/vnd.microsoft.portable-executable" if not metadata.get("is_dll") else "application/x-msdownload"
    elif fmt == "ZIP":
        metadata = parse_zip_metadata(data, file_path=filename)
        mime_type = "application/zip"
    elif fmt == "PYC":
        metadata = parse_pyc_metadata(data)
        mime_type = "application/x-python-code"
    elif fmt == "TEXT":
        metadata = parse_text_metadata(data, file_path=filename)
        mime_type = "text/plain"
    else:
        metadata = {
            "format_type": "UNKNOWN",
            "leading_bytes_hex": data[:32].hex() if data else "",
        }

    return ArtifactInspection(
        target_path=filename,
        size_bytes=size_bytes,
        sha256=sha256_hash,
        format=fmt,
        is_binary=is_binary,
        mime_type=mime_type,
        metadata=metadata,
    )
