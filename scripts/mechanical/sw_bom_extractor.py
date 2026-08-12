#!/usr/bin/env python3
"""
SolidWorks BOM Extractor + Cost Estimator
Extracts BOM from assemblies and generates cost estimates

Output columns:
PartNo, Qty, Material, Mass, Volume, Cost_Estimate, Vendor, Lead_Time, Description

Usage:
    python sw_bom_extractor.py "C:\Projects\Assembly.SLDASM" "C:\Exports\BOM.xlsx" --material-csv materials.csv
"""

import os
import sys
import argparse
import logging
import csv
import json
from pathlib import Path
from typing import Dict, List, Optional
import win32com.client
import pythoncom

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Default material costs (USD/kg) - update with your supplier data
DEFAULT_MATERIAL_COSTS = {
    # Steel
    'A36': 0.80, 'S235JR': 0.85, 'S355JR': 0.95, '1045': 1.20, '4140': 1.80,
    '4340': 2.20, 'Stainless_304': 3.50, 'Stainless_316': 4.20, 'Stainless_430': 2.80,
    # Aluminum
    '6061-T6': 3.20, '6063-T5': 3.00, '7075-T6': 5.50, '5052-H32': 3.30,
    # Plastics
    'ABS': 2.50, 'POM': 3.80, 'Nylon_66': 4.20, 'PEEK': 85.00, 'PTFE': 12.00,
    # Other
    'Bronze': 8.00, 'Brass': 6.50, 'Titanium_Gr5': 45.00,
}

# Manufacturing cost factors (USD/kg) - rough estimates
MANUFACTURING_FACTORS = {
    'CNC_Milling': 15.00,
    'CNC_Turning': 12.00,
    'Laser_Cutting': 8.00,
    'Waterjet': 10.00,
    'Sheet_Metal_Bending': 5.00,
    'Welding': 20.00,
    'Injection_Molding': 3.00,  # per kg, high volume
    'Die_Casting': 4.00,
    'Forging': 8.00,
    '3D_Print_FDM': 25.00,
    '3D_Print_SLA': 40.00,
    '3D_Print_SLS': 60.00,
}

class SWBOMExtractor:
    def __init__(self, visible: bool = False):
        self.sw_app = None
        self.visible = visible
        self.material_costs = DEFAULT_MATERIAL_COSTS.copy()
        self.manufacturing_factors = MANUFACTURING_FACTORS.copy()

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

    def load_material_costs(self, csv_path: str):
        """Load material costs from CSV file"""
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    material = row.get('Material', '').strip()
                    cost_str = row.get('Cost_USD_per_kg', '').strip()
                    if material and cost_str:
                        try:
                            self.material_costs[material] = float(cost_str)
                        except ValueError:
                            pass
            logger.info(f"Loaded {len(self.material_costs)} material costs")
        except Exception as e:
            logger.warning(f"Could not load material costs: {e}")

    def get_bom(self, assembly_path: str) -> List[Dict]:
        """Extract BOM from assembly"""
        bom_items = []
        
        try:
            doc = self.sw_app.OpenDoc6(assembly_path, 2, 0, "", 0, 0)
            if not doc:
                logger.error(f"Failed to open assembly: {assembly_path}")
                return bom_items

            # Get BOM table annotation
            bom_table = doc.Extension.SelectByID2("", "BOMTABLEANNOTATION", 0, 0, 0, False, 0, None, 0)
            
            if not bom_table:
                # Try to get BOM from feature manager
                bom_feat = self._find_bom_feature(doc)
                if bom_feat:
                    bom_table = bom_feat.GetSpecificFeature2()
            
            if bom_table:
                # Get BOM data
                row_count = bom_table.RowCount
                col_count = bom_table.ColumnCount
                
                # Get headers
                headers = []
                for col in range(col_count):
                    header = bom_table.GetText(col, 0)
                    headers.append(header.strip() if header else f"Col_{col}")
                
                # Get rows
                for row in range(1, row_count):
                    item = {}
                    for col, header in enumerate(headers):
                        text = bom_table.GetText(col, row)
                        item[header] = text.strip() if text else ""
                    bom_items.append(item)
            
            # Alternative: Use BOM API directly
            if not bom_items:
                bom_items = self._get_bom_via_api(doc)
            
            self.sw_app.CloseDoc(doc.GetTitle())
            
        except Exception as e:
            logger.error(f"Error extracting BOM: {e}")
        
        return bom_items

    def _find_bom_feature(self, doc):
        """Find BOM feature in feature tree"""
        try:
            feat = doc.FirstFeature()
            while feat:
                if feat.GetTypeName2() == "BomFeat":
                    return feat
                feat = feat.GetNextFeature()
        except:
            pass
        return None

    def _get_bom_via_api(self, doc) -> List[Dict]:
        """Get BOM using SolidWorks BOM API"""
        bom_items = []
        try:
            # Get top-level BOM
            bom = doc.GetBOMTable()
            if bom:
                row_count = bom.RowCount
                for row in range(2, row_count + 1):  # Skip header
                    item = {}
                    # Common BOM columns
                    columns = {
                        'Item_No': 1, 'Part_No': 2, 'Description': 3,
                        'Qty': 4, 'Material': 5, 'Mass': 6,
                        'Volume': 7, 'Cost': 8, 'Vendor': 9,
                        'Lead_Time': 10, 'Configuration': 11
                    }
                    for name, col in columns.items():
                        try:
                            text = bom.GetText(col, row)
                            item[name] = text.strip() if text else ""
                        except:
                            item[name] = ""
                    
                    # Only add if has part number
                    if item.get('Part_No'):
                        bom_items.append(item)
        except Exception as e:
            logger.warning(f"BOM API extraction warning: {e}")
        return bom_items

    def enrich_bom(self, bom_items: List[Dict], process: str = 'CNC_Milling') -> List[Dict]:
        """Enrich BOM with mass, volume, cost estimates"""
        enriched = []
        
        for item in bom_items:
            enriched_item = item.copy()
            
            # Get material
            material = item.get('Material', '').strip()
            if not material:
                material = item.get('Part_No', '').split('-')[0]  # Try part number prefix
            
            # Get mass (kg)
            mass_str = item.get('Mass', '').replace('kg', '').replace('KG', '').strip()
            try:
                mass = float(mass_str) if mass_str else 0.0
            except:
                mass = 0.0
            
            # Get volume (cm3)
            vol_str = item.get('Volume', '').replace('cm3', '').replace('cm^3', '').strip()
            try:
                volume = float(vol_str) if vol_str else 0.0
            except:
                volume = 0.0
            
            # Get quantity
            qty_str = item.get('Qty', item.get('Quantity', '1')).strip()
            try:
                qty = int(qty_str) if qty_str else 1
            except:
                qty = 1
            
            # Material cost
            material_cost_per_kg = self.material_costs.get(material, 2.0)  # Default $2/kg
            material_cost = mass * material_cost_per_kg
            
            # Manufacturing cost
            mfg_factor = self.manufacturing_factors.get(process, 15.0)
            mfg_cost = mass * mfg_factor
            
            # Total cost per unit
            unit_cost = material_cost + mfg_cost
            total_cost = unit_cost * qty
            
            # Add enriched fields
            enriched_item.update({
                'Material': material,
                'Mass_kg': round(mass, 3),
                'Volume_cm3': round(volume, 1),
                'Quantity': qty,
                'Material_Cost_USD': round(material_cost, 2),
                'Mfg_Cost_USD': round(mfg_cost, 2),
                'Unit_Cost_USD': round(unit_cost, 2),
                'Total_Cost_USD': round(total_cost, 2),
                'Process': process,
            })
            
            enriched.append(enriched_item)
        
        return enriched

    def export_excel(self, bom_items: List[Dict], output_path: str):
        """Export BOM to Excel-compatible CSV"""
        if not bom_items:
            logger.warning("No BOM items to export")
            return False

        # Define output columns
        columns = [
            'Item_No', 'Part_No', 'Description', 'Quantity',
            'Material', 'Mass_kg', 'Volume_cm3',
            'Material_Cost_USD', 'Mfg_Cost_USD', 'Unit_Cost_USD', 'Total_Cost_USD',
            'Process', 'Vendor', 'Lead_Time', 'Configuration', 'Notes'
        ]

        try:
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
                writer.writeheader()
                
                for i, item in enumerate(bom_items, 1):
                    row = {'Item_No': str(i)}
                    row.update(item)
                    writer.writerow(row)
            
            logger.info(f"Exported BOM to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False

    def run(self, assembly_path: str, output_path: str, 
            material_csv: str = None, process: str = 'CNC_Milling') -> dict:
        """Main BOM extraction process"""
        if not self.connect():
            return {"success": False, "error": "Cannot connect to SolidWorks"}

        try:
            if material_csv:
                self.load_material_costs(material_csv)

            logger.info(f"Extracting BOM from: {assembly_path}")
            bom_items = self.get_bom(assembly_path)
            
            if not bom_items:
                return {"success": False, "error": "No BOM data extracted"}

            logger.info(f"Found {len(bom_items)} BOM items")
            
            # Enrich with cost estimates
            enriched = self.enrich_bom(bom_items, process)
            
            # Export
            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)
            self.export_excel(enriched, str(output))

            # Summary
            total_cost = sum(item.get('Total_Cost_USD', 0) for item in enriched)
            total_mass = sum(item.get('Mass_kg', 0) * item.get('Quantity', 1) for item in enriched)

            return {
                "success": True,
                "items_count": len(enriched),
                "total_mass_kg": round(total_mass, 2),
                "total_cost_usd": round(total_cost, 2),
                "output_file": str(output)
            }

        finally:
            self.disconnect()


def main():
    parser = argparse.ArgumentParser(description="SolidWorks BOM Extractor + Cost Estimator")
    parser.add_argument("assembly", help="Path to .SLDASM file")
    parser.add_argument("output", help="Output CSV/Excel file path")
    parser.add_argument("--material-csv", help="CSV with Material,Cost_USD_per_kg columns")
    parser.add_argument("--process", default="CNC_Milling", 
                        choices=list(MANUFACTURING_FACTORS.keys()),
                        help="Manufacturing process for cost estimation")
    parser.add_argument("--visible", action="store_true", help="Show SolidWorks UI")

    args = parser.parse_args()

    extractor = SWBOMExtractor(visible=args.visible)
    result = extractor.run(args.assembly, args.output, args.material_csv, args.process)

    print("\n" + "="*50)
    print("BOM EXTRACTION SUMMARY")
    print("="*50)
    if result.get("success"):
        print(f"Items: {result['items_count']}")
        print(f"Total Mass: {result['total_mass_kg']} kg")
        print(f"Total Cost: ${result['total_cost_usd']:,.2f}")
        print(f"Output: {result['output_file']}")
    else:
        print(f"Failed: {result.get('error')}")
    print("="*50)

    if not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()