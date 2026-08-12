#!/usr/bin/env python3
"""
SolidWorks Sheet Metal Flat Pattern Exporter + Nesting Layout
Exports flat patterns to DXF/DWG with bend tables and generates nesting layouts

Usage:
    python sw_sheetmetal_export.py "C:\Projects" "C:\Exports" --nesting-sheet 1500x3000
"""

import os
import sys
import argparse
import logging
import json
import math
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import win32com.client
import pythoncom

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class SWSheetMetalExporter:
    def __init__(self, visible: bool = False):
        self.sw_app = None
        self.visible = visible
        self.exported_parts = []
        self.errors = []

    def connect(self):
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
        if self.sw_app:
            self.sw_app = None
        pythoncom.CoUninitialize()

    def is_sheet_metal(self, doc) -> bool:
        """Check if document is a sheet metal part"""
        try:
            feat = doc.FirstFeature()
            while feat:
                if feat.GetTypeName2() in ["SheetMetal", "BaseFlange", "SheetMetalFeatureData"]:
                    return True
                feat = feat.GetNextFeature()
        except:
            pass
        return False

    def get_sheet_metal_info(self, doc) -> Dict:
        """Extract sheet metal parameters"""
        info = {
            'thickness': 0.0,
            'bend_radius': 0.0,
            'k_factor': 0.5,
            'bend_allowance_type': 'K_FACTOR',
            'bends': [],
            'flat_pattern_area': 0.0,
        }
        
        try:
            # Get sheet metal feature
            feat = doc.FirstFeature()
            while feat:
                if feat.GetTypeName2() == "SheetMetal":
                    data = feat.GetDefinition()
                    if data:
                        info['thickness'] = data.Thickness * 1000  # Convert to mm
                        info['bend_radius'] = data.DefaultBendRadius * 1000
                        info['k_factor'] = data.KFactor
                        info['bend_allowance_type'] = data.BendAllowanceType
                    break
                feat = feat.GetNextFeature()

            # Get flat pattern
            flat_pattern = doc.GetFlatPattern()
            if flat_pattern:
                # Get bend lines
                bend_lines = flat_pattern.GetBendLines()
                for bl in bend_lines:
                    info['bends'].append({
                        'angle': bl.Angle * 180 / math.pi,  # radians to degrees
                        'radius': bl.Radius * 1000,
                        'length': bl.Length * 1000,
                        'direction': 'Up' if bl.Direction else 'Down'
                    })
                
                # Get flat pattern bounding box area
                bbox = flat_pattern.GetBoundingBox()
                if bbox:
                    width = (bbox[3] - bbox[0]) * 1000
                    height = (bbox[4] - bbox[1]) * 1000
                    info['flat_pattern_area'] = width * height / 1000000  # m2
                    info['bbox_width'] = width
                    info['bbox_height'] = height

        except Exception as e:
            logger.warning(f"Could not get sheet metal info: {e}")

        return info

    def export_flat_pattern(self, doc, output_path: Path, formats: List[str] = None) -> bool:
        """Export flat pattern to DXF/DWG"""
        if formats is None:
            formats = ['dxf']

        try:
            flat_pattern = doc.GetFlatPattern()
            if not flat_pattern:
                logger.warning("No flat pattern found")
                return False

            # Export flat pattern view
            for fmt in formats:
                if fmt == 'dxf':
                    # Export flat pattern as DXF
                    flat_pattern.ExportFlatPatternView(str(output_path.with_suffix('.dxf')))
                elif fmt == 'dwg':
                    flat_pattern.ExportFlatPatternView(str(output_path.with_suffix('.dwg')))
                elif fmt == 'pdf':
                    # Create drawing of flat pattern and export PDF
                    self._create_flat_pattern_drawing(doc, output_path)

            logger.info(f"Exported flat pattern: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Flat pattern export failed: {e}")
            return False

    def _create_flat_pattern_drawing(self, doc, output_path: Path):
        """Create a drawing document with flat pattern view"""
        try:
            # Create drawing
            drawing = self.sw_app.NewDrawing()
            sheet = drawing.GetCurrentSheet()
            
            # Insert flat pattern view
            view = drawing.CreateFlatPatternViewFromModelView3(
                doc.GetPathName(), "*Front", 0, 0, 0
            )
            
            if view:
                # Add bend table
                drawing.InsertBendTable(0.05, 0.05, True)
                
                # Add bend notes
                drawing.InsertBendNotes()
                
                # Export to PDF
                drawing.SaveAs3(str(output_path.with_suffix('.pdf')), 0, 22)
            
            self.sw_app.CloseDoc(drawing.GetTitle())
            
        except Exception as e:
            logger.warning(f"Flat pattern drawing creation failed: {e}")

    def generate_nesting_layout(self, parts_info: List[Dict], 
                                 sheet_width: float, sheet_height: float,
                                 spacing: float = 10.0) -> Dict:
        """Generate simple nesting layout (rectangular packing)"""
        # Sort parts by area descending (largest first)
        sorted_parts = sorted(parts_info, key=lambda p: p.get('area', 0), reverse=True)
        
        # Simple shelf packing algorithm
        placements = []
        current_x = spacing
        current_y = spacing
        row_height = 0
        
        for part in sorted_parts:
            w = part.get('bbox_width', 0) + spacing
            h = part.get('bbox_height', 0) + spacing
            
            # Check if fits in current row
            if current_x + w > sheet_width - spacing:
                # New row
                current_x = spacing
                current_y += row_height + spacing
                row_height = 0
            
            # Check if fits in sheet
            if current_y + h > sheet_height - spacing:
                logger.warning(f"Part {part.get('name')} doesn't fit on sheet")
                continue
            
            placements.append({
                'part_name': part.get('name'),
                'x': current_x,
                'y': current_y,
                'rotation': 0,
                'width': w - spacing,
                'height': h - spacing
            })
            
            current_x += w
            row_height = max(row_height, h)
        
        # Calculate utilization
        total_part_area = sum(p.get('area', 0) for p in parts_info)
        sheet_area = sheet_width * sheet_height / 1000000  # m2
        utilization = (total_part_area / sheet_area * 100) if sheet_area > 0 else 0
        
        return {
            'placements': placements,
            'sheet_width': sheet_width,
            'sheet_height': sheet_height,
            'utilization_percent': round(utilization, 1),
            'parts_placed': len(placements),
            'total_parts': len(parts_info)
        }

    def export_nesting_dxf(self, nesting_result: Dict, output_path: Path):
        """Export nesting layout as DXF"""
        try:
            import ezdxf
        except ImportError:
            logger.warning("ezdxf not installed, skipping DXF export")
            return False

        try:
            doc = ezdxf.new()
            msp = doc.modelspace()
            
            # Draw sheet boundary
            sheet_w = nesting_result['sheet_width']
            sheet_h = nesting_result['sheet_height']
            msp.add_lwpolyline([
                (0, 0), (sheet_w, 0), (sheet_w, sheet_h), (0, sheet_h), (0, 0)
            ], dxfattribs={'layer': 'SHEET', 'color': 7})
            
            # Draw part placements
            for i, placement in enumerate(nesting_result['placements']):
                x, y = placement['x'], placement['y']
                w, h = placement['width'], placement['height']
                
                # Part outline
                msp.add_lwpolyline([
                    (x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)
                ], dxfattribs={'layer': 'PARTS', 'color': 3})
                
                # Part label
                msp.add_text(
                    f"{placement['part_name']} ({i+1})",
                    dxfattribs={'height': 10, 'layer': 'LABELS'}
                ).set_pos((x + w/2, y + h/2), align='MIDDLE_CENTER')
            
            # Add info text
            info_text = (
                f"Nesting Layout\n"
                f"Sheet: {sheet_w:.0f} x {sheet_h:.0f} mm\n"
                f"Utilization: {nesting_result['utilization_percent']}%\n"
                f"Parts: {nesting_result['parts_placed']}/{nesting_result['total_parts']}"
            )
            msp.add_mtext(info_text, dxfattribs={'layer': 'INFO'}).set_location((10, sheet_h - 20))
            
            doc.saveas(str(output_path))
            logger.info(f"Nesting DXF exported: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Nesting DXF export failed: {e}")
            return False

    def run(self, source_dir: str, output_dir: str, 
            nesting_sheet: str = "1500x3000",
            formats: List[str] = None) -> dict:
        """Main sheet metal export process"""
        if not self.connect():
            return {"success": False, "error": "Cannot connect to SolidWorks"}

        if formats is None:
            formats = ['dxf']

        try:
            source = Path(source_dir)
            output = Path(output_dir)
            output.mkdir(parents=True, exist_ok=True)

            # Parse nesting sheet size
            sheet_w, sheet_h = map(float, nesting_sheet.lower().split('x'))
            
            # Find all sheet metal parts
            sm_files = list(source.rglob('*.SLDPRT'))
            sheet_metal_parts = []
            parts_info = []

            for file_path in sm_files:
                logger.info(f"Checking: {file_path}")
                doc = self.sw_app.OpenDoc6(str(file_path), 1, 0, "", 0, 0)
                if not doc:
                    continue

                if self.is_sheet_metal(doc):
                    info = self.get_sheet_metal_info(doc)
                    info['name'] = file_path.stem
                    info['path'] = file_path
                    parts_info.append(info)

                    # Export flat pattern
                    part_output_dir = output / file_path.relative_to(source).parent / file_path.stem
                    part_output_dir.mkdir(parents=True, exist_ok=True)
                    
                    self.export_flat_pattern(doc, part_output_dir / file_path.stem, formats)
                    
                    # Export bend table as CSV
                    self._export_bend_table(doc, info, part_output_dir / f"{file_path.stem}_bends.csv")

                    sheet_metal_parts.append(file_path.stem)
                
                self.sw_app.CloseDoc(doc.GetTitle())

            # Generate nesting layout
            if parts_info:
                nesting = self.generate_nesting_layout(parts_info, sheet_w, sheet_h)
                self.export_nesting_dxf(nesting, output / "nesting_layout.dxf")
                
                # Export nesting report
                with open(output / "nesting_report.json", 'w') as f:
                    json.dump(nesting, f, indent=2)

            return {
                "success": True,
                "sheet_metal_parts": len(sheet_metal_parts),
                "parts_processed": sheet_metal_parts,
                "nesting": nesting if parts_info else None,
                "errors": self.errors
            }

        finally:
            self.disconnect()

    def _export_bend_table(self, doc, info: Dict, output_path: Path):
        """Export bend table as CSV"""
        import csv
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Bend #', 'Angle (deg)', 'Radius (mm)', 'Length (mm)', 'Direction'])
                for i, bend in enumerate(info.get('bends', []), 1):
                    writer.writerow([
                        i, bend['angle'], bend['radius'], bend['length'], bend['direction']
                    ])
        except Exception as e:
            logger.warning(f"Bend table export failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="SolidWorks Sheet Metal Flat Pattern + Nesting")
    parser.add_argument("source", help="Source directory with sheet metal parts")
    parser.add_argument("output", help="Output directory")
    parser.add_argument("--nesting-sheet", default="1500x3000", help="Sheet size WxH in mm")
    parser.add_argument("--formats", default="dxf,pdf", help="Export formats: dxf,dwg,pdf")
    parser.add_argument("--visible", action="store_true", help="Show SolidWorks UI")

    args = parser.parse_args()

    formats = [f.strip().lower() for f in args.formats.split(',')]

    exporter = SWSheetMetalExporter(visible=args.visible)
    result = exporter.run(args.source, args.output, args.nesting_sheet, formats)

    print("\n" + "="*50)
    print("SHEET METAL EXPORT SUMMARY")
    print("="*50)
    print(f"Sheet metal parts found: {result.get('sheet_metal_parts', 0)}")
    for p in result.get('parts_processed', []):
        print(f"  ✅ {p}")
    
    if result.get('nesting'):
        n = result['nesting']
        print(f"\nNesting Layout:")
        print(f"  Sheet: {n['sheet_width']} x {n['sheet_height']} mm")
        print(f"  Utilization: {n['utilization_percent']}%")
        print(f"  Parts placed: {n['parts_placed']}/{n['total_parts']}")
    
    if result.get('errors'):
        print(f"\nErrors: {len(result['errors'])}")
    
    print("="*50)

    if not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()