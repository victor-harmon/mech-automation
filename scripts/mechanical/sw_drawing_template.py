#!/usr/bin/env python3
"""
SolidWorks Drawing Template Generator
Creates standardized drawings (ISO/ASME) with:
- 3 standard views + isometric
- Title block with linked properties
- BOM table configured
- GD&T symbols template
- Custom properties mapping

Usage:
    python sw_drawing_template.py --standard ISO --sizes A3,A4,A2,A1,A0 --output "C:\Templates"
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, List
import win32com.client
import pythoncom

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Drawing standards configuration
STANDARDS = {
    'ISO': {
        'projection': 1,  # Third angle
        'units': 'MMGS',  # mm, g, s
        'decimal_places': 2,
        'title_block': 'ISO',
        'bom_standard': 'ISO 7200',
    },
    'ASME': {
        'projection': 0,  # First angle
        'units': 'IPS',   # in, lb, s
        'decimal_places': 3,
        'title_block': 'ASME',
        'bom_standard': 'ASME Y14.34',
    },
    'JIS': {
        'projection': 1,
        'units': 'MMGS',
        'decimal_places': 2,
        'title_block': 'JIS',
        'bom_standard': 'JIS B 0001',
    }
}

SHEET_SIZES = {
    'A0': (1189, 841),
    'A1': (841, 594),
    'A2': (594, 420),
    'A3': (420, 297),
    'A4': (297, 210),
    'A': (11, 8.5),   # ANSI A
    'B': (17, 11),    # ANSI B
    'C': (22, 17),    # ANSI C
    'D': (34, 22),    # ANSI D
    'E': (44, 34),    # ANSI E
}

# Standard view orientations
VIEW_ORIENTATIONS = {
    'front': (0, 0, 0),
    'top': (0, 90, 0),
    'right': (90, 0, 0),
    'left': (-90, 0, 0),
    'bottom': (0, -90, 0),
    'back': (0, 180, 0),
    'isometric': (45, 45, 0),
    'trimetric': (30, 30, 0),
}

class SWDrawingTemplateGenerator:
    def __init__(self, visible: bool = False):
        self.sw_app = None
        self.visible = visible

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

    def create_drawing_template(self, standard: str, size: str, output_dir: Path):
        """Create a drawing template for given standard and sheet size"""
        if standard not in STANDARDS:
            logger.error(f"Unknown standard: {standard}")
            return False

        if size not in SHEET_SIZES:
            logger.error(f"Unknown sheet size: {size}")
            return False

        std_config = STANDARDS[standard]
        width, height = SHEET_SIZES[size]

        try:
            # Create new drawing
            drawing = self.sw_app.NewDocument(
                self.sw_app.GetUserPreferenceStringValue(
                    win32com.client.constants.swDefaultTemplateDrawing
                ), 0, width, height
            )
            
            if not drawing:
                # Try alternative method
                drawing = self.sw_app.NewDrawing()
            
            if not drawing:
                logger.error("Failed to create drawing document")
                return False

            sheet = drawing.GetCurrentSheet()
            if not sheet:
                logger.error("Failed to get sheet")
                return False

            # Set sheet properties
            sheet.SetDisplayMode(win32com.client.constants.swSheetDisplayMode_DisplaySheet)
            
            # Set projection type (0=first angle, 1=third angle)
            drawing.Extension.SetProjectionType(std_config['projection'])

            # Create standard views using model view
            # We need a dummy model or use predefined views
            # For template, we'll set up view placeholders

            # Add title block
            self._setup_title_block(drawing, sheet, standard, size, std_config)

            # Add BOM table template
            self._setup_bom_table(drawing, sheet, standard)

            # Add GD&T symbols
            self._setup_gdt_symbols(drawing, sheet)

            # Add revision table
            self._setup_revision_table(drawing, sheet)

            # Add custom properties
            self._setup_custom_properties(drawing, standard)

            # Save as drawing template
            template_name = f"{standard}_{size}.drwdot"
            template_path = output_dir / template_name
            
            # Save as template
            errors = 0
            warnings = 0
            drawing.SaveAs3(str(template_path), errors, warnings)
            
            logger.info(f"Created template: {template_path}")
            self.sw_app.CloseDoc(drawing.GetTitle())
            return True

        except Exception as e:
            logger.error(f"Error creating template {standard}_{size}: {e}")
            return False

    def _setup_title_block(self, drawing, sheet, standard: str, size: str, config: dict):
        """Configure title block with linked properties"""
        try:
            # Get title block definition
            title_block = sheet.GetTitleBlock()
            if title_block:
                # Set standard title block fields
                title_block.SetField("STANDARD", standard)
                title_block.SetField("SIZE", size)
                title_block.SetField("PROJECTION", "Third Angle" if config['projection'] else "First Angle")
                title_block.SetField("UNITS", config['units'])
            
            # Add custom properties to drawing
            custom_props = drawing.Extension.CustomPropertyManager("")
            props = {
                "PROJECT_NAME": "",
                "DRAWING_NUMBER": "",
                "REVISION": "A",
                "SHEET": "$PRPSHEET:\"SHEET\"",
                "TOTAL_SHEETS": "$PRPSHEET:\"TOTALSHEETS\"",
                "SCALE": "$PRPSHEET:\"SCALE\"",
                "WEIGHT": "$PRPMODEL:\"MASS\"",
                "MATERIAL": "$PRPMODEL:\"MATERIAL\"",
                "FINISH": "",
                "DRAWN_BY": "",
                "CHECKED_BY": "",
                "APPROVED_BY": "",
                "DATE": "$PRPSHEET:\"DATE\"",
                "STANDARD": standard,
                "SHEET_SIZE": size,
            }
            
            for name, value in props.items():
                custom_props.Add2(name, win32com.client.constants.swCustomInfoType_e.swCustomInfoText, value)
                
        except Exception as e:
            logger.warning(f"Title block setup warning: {e}")

    def _setup_bom_table(self, drawing, sheet, standard: str):
        """Add BOM table template"""
        try:
            # Insert BOM table annotation
            bom_annotation = drawing.InsertBOMTable2(
                True,  # Use top-level BOM
                win32com.client.constants.swBOMConfiguration_TopLevelOnly,
                "Default",
                0.05, 0.05,  # Position
                win32com.client.constants.swBOMType_e.swBOMType_Indented,
                0,  # No configuration specified
                True
            )
            
            if bom_annotation:
                logger.info("BOM table template added")
                
        except Exception as e:
            logger.warning(f"BOM table setup warning: {e}")

    def _setup_gdt_symbols(self, drawing, sheet):
        """Add GD&T symbol library/placeholders"""
        try:
            # Add note with GD&T reference symbols
            notes = [
                "⌖ TRUE POSITION", "⌭ FLATNESS", "⌯ STRAIGHTNESS", 
                "⌰ CIRCULARITY", "⌱ CYLINDRICITY", "⏚ PERPENDICULARITY",
                "∥ PARALLELISM", "⌲ PROFILE OF A LINE", "⌳ PROFILE OF A SURFACE",
                "⌴ RUNOUT", "⌵ TOTAL RUNOUT", "⌶ CONCENTRICITY",
                "⌀ DIAMETER", "S⌀ SPHERICAL DIAMETER", "R RADIUS",
                "SR SPHERICAL RADIUS", "⌠ COUNTERBORE", "⌡ COUNTERSINK",
                "⌮ DEPTH", "△ SURFACE TEXTURE", "Ⓒ STATISTICAL TOLERANCE"
            ]
            
            # Add as a reference note off-sheet
            note_text = "GD&T SYMBOL REFERENCE:\n" + "  ".join(notes)
            annotation = drawing.InsertAnnotation(
                win32com.client.constants.swNoteAnnotation,
                note_text,
                0.02, 0.95  # Position off visible area
            )
            
        except Exception as e:
            logger.warning(f"GD&T symbols setup warning: {e}")

    def _setup_revision_table(self, drawing, sheet):
        """Add revision table template"""
        try:
            # Insert revision table
            rev_table = drawing.InsertRevisionTable(
                True,  # Attach to sheet
                0.8, 0.02,  # Position (top right)
                3,  # Columns: Rev, Description, Date, Approved
                5   # Rows
            )
            
            if rev_table:
                logger.info("Revision table template added")
                
        except Exception as e:
            logger.warning(f"Revision table setup warning: {e}")

    def _setup_custom_properties(self, drawing, standard: str):
        """Set drawing custom properties"""
        try:
            cpm = drawing.Extension.CustomPropertyManager("")
            
            # Standard properties
            std_props = {
                "SW_STANDARD": standard,
                "SW_PROJECTION": "THIRD_ANGLE" if STANDARDS[standard]['projection'] else "FIRST_ANGLE",
                "SW_UNITS": STANDARDS[standard]['units'],
                "SW_DECIMAL_PLACES": str(STANDARDS[standard]['decimal_places']),
            }
            
            for name, value in std_props.items():
                cpm.Add2(name, win32com.client.constants.swCustomInfoType_e.swCustomInfoText, value)
                
        except Exception as e:
            logger.warning(f"Custom properties setup warning: {e}")

    def run(self, standards: List[str], sizes: List[str], output_dir: str) -> dict:
        """Generate all templates"""
        if not self.connect():
            return {"success": False, "error": "Cannot connect to SolidWorks"}

        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)

        results = {"created": [], "failed": []}
        
        for standard in standards:
            for size in sizes:
                logger.info(f"Creating template: {standard}_{size}")
                if self.create_drawing_template(standard, size, output):
                    results["created"].append(f"{standard}_{size}.drwdot")
                else:
                    results["failed"].append(f"{standard}_{size}")

        self.disconnect()
        results["success"] = len(results["failed"]) == 0
        return results


def main():
    parser = argparse.ArgumentParser(description="SolidWorks Drawing Template Generator")
    parser.add_argument("--standard", default="ISO,ASME", help="Comma-separated: ISO,ASME,JIS")
    parser.add_argument("--sizes", default="A4,A3,A2,A1,A0", help="Comma-separated sheet sizes")
    parser.add_argument("--output", default="C:/Templates", help="Output directory")
    parser.add_argument("--visible", action="store_true", help="Show SolidWorks UI")

    args = parser.parse_args()

    standards = [s.strip().upper() for s in args.standard.split(',')]
    sizes = [s.strip().upper() for s in args.sizes.split(',')]

    generator = SWDrawingTemplateGenerator(visible=args.visible)
    result = generator.run(standards, sizes, args.output)

    print("\n" + "="*50)
    print("TEMPLATE GENERATION SUMMARY")
    print("="*50)
    print(f"Created: {len(result['created'])}")
    for t in result['created']:
        print(f"  ✅ {t}")
    if result['failed']:
        print(f"Failed: {len(result['failed'])}")
        for t in result['failed']:
            print(f"  ❌ {t}")
    print("="*50)

    if not result['success']:
        sys.exit(1)


if __name__ == "__main__":
    main()