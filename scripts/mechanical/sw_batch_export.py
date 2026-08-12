#!/usr/bin/env python3
"""
SolidWorks Batch Export Tool
Export .SLDPRT/.SLDASM files to multiple formats:
STEP, STL, PDF, DXF, glTF, 3D PDF, BOM Excel

Usage:
    python sw_batch_export.py "C:\Projects" "C:\Exports" --formats step,stl,pdf,dxf,gltf
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Optional
import win32com.client
import pythoncom

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# SolidWorks export format constants
EXPORT_FORMATS = {
    'step': (80, 'STEP AP242'),
    'stl': (3, 'STL'),
    'pdf': (22, 'PDF'),
    'dxf': (7, 'DXF'),
    'gltf': (45, 'glTF'),
    '3dpdf': (23, '3D PDF'),
    'iges': (6, 'IGES'),
    'parasolid': (34, 'Parasolid'),
    'jpg': (17, 'JPEG'),
    'png': (18, 'PNG'),
}

class SWBatchExporter:
    def __init__(self, visible: bool = False):
        self.sw_app = None
        self.visible = visible
        self.export_counts = {fmt: 0 for fmt in EXPORT_FORMATS}
        self.errors = []

    def connect(self):
        """Connect to SolidWorks application"""
        try:
            pythoncom.CoInitialize()
            self.sw_app = win32com.client.Dispatch("SldWorks.Application")
            self.sw_app.Visible = self.visible
            logger.info(f"Connected to SolidWorks {self.sw_app.RevisionNumber()}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to SolidWorks: {e}")
            return False

    def disconnect(self):
        """Disconnect from SolidWorks"""
        if self.sw_app:
            self.sw_app = None
        pythoncom.CoUninitialize()

    def find_files(self, source_dir: str, extensions: List[str] = None) -> List[Path]:
        """Find all SolidWorks files in source directory"""
        if extensions is None:
            extensions = ['.SLDPRT', '.SLDASM', '.SLDDRW']
        
        source = Path(source_dir)
        files = []
        for ext in extensions:
            files.extend(source.rglob(f'*{ext}'))
        return files

    def export_file(self, file_path: Path, output_dir: Path, formats: List[str]) -> bool:
        """Export a single file to multiple formats"""
        try:
            # Open document
            doc = self.sw_app.OpenDoc6(str(file_path), 1, 0, "", 0, 0)
            if not doc:
                logger.error(f"Failed to open: {file_path}")
                return False

            base_name = file_path.stem
            file_output_dir = output_dir / file_path.relative_to(file_path.anchor).parent / base_name
            file_output_dir.mkdir(parents=True, exist_ok=True)

            success = True
            for fmt in formats:
                if fmt not in EXPORT_FORMATS:
                    logger.warning(f"Unknown format: {fmt}")
                    continue

                fmt_id, fmt_name = EXPORT_FORMATS[fmt]
                output_file = file_output_dir / f"{base_name}.{fmt}"

                try:
                    if fmt == 'step':
                        # STEP AP242
                        doc.SaveAs3(str(output_file), 0, 2)
                    elif fmt == 'stl':
                        # STL with fine resolution
                        stl_opt = doc.Extension.GetExportFileData(3)
                        stl_opt[0] = 1  # Fine resolution
                        doc.SaveAs3(str(output_file), 0, 3)
                    elif fmt == 'pdf':
                        doc.SaveAs3(str(output_file), 0, 22)
                    elif fmt == 'dxf':
                        doc.SaveAs3(str(output_file), 0, 7)
                    elif fmt == 'gltf':
                        doc.SaveAs3(str(output_file), 0, 45)
                    elif fmt == '3dpdf':
                        doc.SaveAs3(str(output_file), 0, 23)
                    elif fmt == 'iges':
                        doc.SaveAs3(str(output_file), 0, 6)
                    elif fmt == 'parasolid':
                        doc.SaveAs3(str(output_file), 0, 34)
                    else:
                        doc.SaveAs3(str(output_file), 0, fmt_id)

                    self.export_counts[fmt] += 1
                    logger.info(f"Exported {fmt_name}: {output_file}")

                except Exception as e:
                    logger.error(f"Failed to export {fmt} for {file_path}: {e}")
                    self.errors.append(f"{file_path} -> {fmt}: {e}")
                    success = False

            # Close document
            self.sw_app.CloseDoc(doc.GetTitle())
            return success

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            self.errors.append(f"{file_path}: {e}")
            return False

    def run(self, source_dir: str, output_dir: str, formats: List[str], 
            extensions: List[str] = None) -> dict:
        """Main export process"""
        if not self.connect():
            return {"success": False, "error": "Cannot connect to SolidWorks"}

        try:
            source = Path(source_dir)
            output = Path(output_dir)
            output.mkdir(parents=True, exist_ok=True)

            files = self.find_files(source_dir, extensions)
            logger.info(f"Found {len(files)} files to export")

            if not files:
                return {"success": True, "message": "No files found", "counts": self.export_counts}

            processed = 0
            for file_path in files:
                logger.info(f"Processing ({processed+1}/{len(files)}): {file_path}")
                self.export_file(file_path, Path(output_dir), formats)
                processed += 1

            return {
                "success": True,
                "processed": processed,
                "counts": self.export_counts,
                "errors": self.errors
            }

        finally:
            self.disconnect()


def main():
    parser = argparse.ArgumentParser(description="SolidWorks Batch Export Tool")
    parser.add_argument("source", help="Source directory with SolidWorks files")
    parser.add_argument("output", help="Output directory for exported files")
    parser.add_argument("--formats", default="step,stl,pdf,dxf",
                        help="Comma-separated formats: step,stl,pdf,dxf,gltf,3dpdf,iges,parasolid")
    parser.add_argument("--extensions", default="SLDPRT,SLDASM",
                        help="Comma-separated file extensions")
    parser.add_argument("--visible", action="store_true", help="Show SolidWorks UI")

    args = parser.parse_args()

    formats = [f.strip().lower() for f in args.formats.split(',')]
    extensions = [f".{e.strip().upper()}" for e in args.extensions.split(',')]

    exporter = SWBatchExporter(visible=args.visible)
    result = exporter.run(args.source, args.output, formats, extensions)

    if result.get("success"):
        print("\n" + "="*50)
        print("EXPORT SUMMARY")
        print("="*50)
        for fmt, count in result["counts"].items():
            if count > 0:
                fmt_name = EXPORT_FORMATS.get(fmt, (0, fmt))[1]
                print(f"  {fmt_name}: {count} files")
        if result.get("errors"):
            print(f"\nErrors: {len(result['errors'])}")
            for err in result["errors"][:5]:
                print(f"  - {err}")
        print("="*50)
    else:
        print(f"Export failed: {result.get('error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()