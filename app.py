"""
app_local.py - Life Test Data Analysis Desktop Application

Simplified local GUI with automatic spec file detection and test type auto-detection.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import pandas as pd
from datetime import datetime
import threading

from core.pivot_generator import UnifiedPivotGenerator
from core.Spec_Category_config import Paperpath_CATEGORIES, ADF_CATEGORIES
from core.excel_formatter import ExcelFormatter


class PivotGeneratorApp:
    """Desktop GUI for generating pivot tables with auto-detection."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Life Test Data Analysis")
        self.root.geometry("800x550")
        
        # Variables
        self.raw_data_file = tk.StringVar()
        self.output_folder = tk.StringVar(value=str(Path.cwd()))
        
        # Spec file is always in current directory
        self.spec_file_path = Path.cwd() / "spec.xlsx"
        
        # Create UI
        self.create_widgets()
        
    def create_widgets(self):
        """Create all UI widgets."""
        
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Life Test Data Analysis", 
                                font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Raw Data File Section
        row = 1
        ttk.Label(main_frame, text="Raw Data File:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        ttk.Entry(main_frame, textvariable=self.raw_data_file, width=60).grid(
            row=row, column=1, sticky=(tk.W, tk.E), padx=5
        )
        ttk.Button(main_frame, text="Browse...", command=self.browse_raw_data).grid(
            row=row, column=2, padx=5
        )
        
        # Output Folder Section
        row += 1
        ttk.Label(main_frame, text="Output Folder:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        ttk.Entry(main_frame, textvariable=self.output_folder, width=60).grid(
            row=row, column=1, sticky=(tk.W, tk.E), padx=5
        )
        ttk.Button(main_frame, text="Browse...", command=self.browse_output_folder).grid(
            row=row, column=2, padx=5
        )
        
        # Info Label
        row += 1
        info_text = "• Test type will be auto-detected\n• Spec file: spec.xlsx (current folder)"
        ttk.Label(main_frame, text=info_text, foreground="gray", 
                 justify=tk.LEFT, font=('Arial', 9)).grid(
            row=row, column=0, columnspan=3, pady=10, sticky=tk.W
        )
        
        # Generate Button
        row += 1
        self.generate_btn = ttk.Button(main_frame, text="Generate Pivot Tables", 
                                       command=self.generate_pivots)
        self.generate_btn.grid(row=row, column=0, columnspan=3, pady=20)
        
        # Progress Bar
        row += 1
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # Status Label
        row += 1
        self.status_label = ttk.Label(main_frame, text="Ready", foreground="blue")
        self.status_label.grid(row=row, column=0, columnspan=3, pady=5)
        
        # Log Section
        row += 1
        ttk.Label(main_frame, text="Log:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(10, 5)
        )
        
        row += 1
        self.log_text = scrolledtext.ScrolledText(main_frame, height=15, width=80, 
                                                   wrap=tk.WORD, state='disabled')
        self.log_text.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        main_frame.rowconfigure(row, weight=1)
        
        # Instructions
        row += 1
        instructions = """
Instructions:
1. Select your raw data file (Excel format)
2. Choose output folder
3. Click "Generate Pivot Tables"
4. System will auto-detect test type (Paperpath/ADF)
5. Results will be saved to output folder
        """
        ttk.Label(main_frame, text=instructions, justify=tk.LEFT, 
                 foreground="gray").grid(row=row, column=0, columnspan=3, pady=10, sticky=tk.W)
    
    def browse_raw_data(self):
        """Browse for raw data file."""
        filename = filedialog.askopenfilename(
            title="Select Raw Data File",
            filetypes=[
                ("Excel files", "*.xlsx *.xlsm *.xls"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.raw_data_file.set(filename)
            self.log(f"Selected raw data: {filename}")
    
    def browse_output_folder(self):
        """Browse for output folder."""
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder.set(folder)
            self.log(f"Output folder: {folder}")
    
    def log(self, message):
        """Add message to log."""
        self.log_text.config(state='normal')
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.root.update()
    
    def update_status(self, message, color="blue"):
        """Update status label."""
        self.status_label.config(text=message, foreground=color)
        self.root.update()
    
    def generate_pivots(self):
        """Generate pivot tables in a separate thread."""
        if not self.raw_data_file.get():
            messagebox.showerror("Error", "Please select a raw data file!")
            return
        
        if not Path(self.raw_data_file.get()).exists():
            messagebox.showerror("Error", "Raw data file does not exist!")
            return
        
        # Disable button and start progress
        self.generate_btn.config(state='disabled')
        self.progress.start()
        
        # Run in thread
        thread = threading.Thread(target=self._generate_pivots_thread, daemon=True)
        thread.start()
    
    def _generate_pivots_thread(self):
        """Worker thread for generating pivots."""
        try:
            self.update_status("Starting generation...", "blue")
            self.log("="*60)
            self.log("GENERATING PIVOT TABLES")
            self.log("="*60)
            
            raw_file = self.raw_data_file.get()
            
            # Check if spec file exists
            if self.spec_file_path.exists():
                spec_file = str(self.spec_file_path)
                self.log(f"✓ Using spec file: {self.spec_file_path.name}")
            else:
                spec_file = None
                self.log("⚠ Spec file not found - validation will be skipped")
            
            # Auto-detect test type using first Paperpath category
            self.log("\nAuto-detecting test type...")
            temp_gen = UnifiedPivotGenerator(raw_file, Paperpath_CATEGORIES[0], spec_file)
            detected_sub_assembly = temp_gen.sub_assembly
            product = temp_gen.product
            sheet_name = temp_gen.spec_sheet
            
            # Choose correct test categories based on detected sub-assembly
            if detected_sub_assembly.upper() == "ADF":
                test_categories = ADF_CATEGORIES
                test_type_name = "ADF"
            else:
                test_categories = Paperpath_CATEGORIES
                test_type_name = "Paperpath"
            
            self.log(f"✓ Detected Test Type: {test_type_name}")
            self.log(f"✓ Product: {product}")
            self.log(f"✓ Sheet: {sheet_name}")
            self.log(f"\nProcessing {len(test_categories)} categories...")
            
            all_pivots = {}
            
            # Generate pivots for each category
            for idx, config in enumerate(test_categories, 1):
                self.update_status(f"Processing {config.name}... ({idx}/{len(test_categories)})", "blue")
                self.log(f"\n[{idx}/{len(test_categories)}] Generating: {config.name}")
                
                generator = UnifiedPivotGenerator(raw_file, config, spec_file)
                pivot_media = generator.create_pivot_by_media_name()
                pivot_unit = generator.create_pivot_by_unit()
                
                all_pivots[config.name] = {
                    'media': pivot_media,
                    'unit': pivot_unit,
                    'config': config
                }
                
                self.log(f"    ✓ Complete")
            
            # Save to Excel
            self.update_status("Saving to Excel...", "blue")
            self.log("\nSaving to Excel...")
            
            # Auto-generate filename like master_pivot_generator
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"{product}_{sheet_name}_Pivot_Tables_{timestamp}.xlsx"
            output_path = Path(self.output_folder.get()) / output_filename
            
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                formatter = ExcelFormatter()
                
                for category_name, pivot_data in all_pivots.items():
                    config = pivot_data['config']
                    
                    sheet_media = f'{category_name} By Media'
                    sheet_unit = f'{category_name} By Unit'
                    
                    pivot_data['media'].to_excel(writer, sheet_name=sheet_media, index=False)
                    pivot_data['unit'].to_excel(writer, sheet_name=sheet_unit, index=False)
                    
                    formatter.apply_standard_formatting(
                        worksheet=writer.sheets[sheet_media],
                        dataframe=pivot_data['media'],
                        grand_total_identifier='Grand Total',
                        bold_columns=[config.total_column_name],
                        highlight_threshold=0.5
                    )
                    
                    formatter.apply_standard_formatting(
                        worksheet=writer.sheets[sheet_unit],
                        dataframe=pivot_data['unit'],
                        grand_total_identifier='Grand Total',
                        bold_columns=[config.total_column_name],
                        highlight_threshold=0.5
                    )
            
            self.log(f"\n✓ Saved: {output_filename}")
            self.log("="*60)
            self.log("SUCCESS!")
            self.log("="*60)
            
            self.update_status("Complete! ✓", "green")
            
            # Show success message
            self.root.after(0, lambda fn=output_filename, of=self.output_folder.get(): messagebox.showinfo(
                "Success", 
                f"Pivot tables generated successfully!\n\nFile: {fn}\nLocation: {of}"
            ))
            
        except Exception as e:
            error_msg = str(e)
            self.log(f"\n✗ ERROR: {error_msg}")
            import traceback
            traceback_str = traceback.format_exc()
            self.log(traceback_str)
            self.update_status("Error! ✗", "red")
            self.root.after(0, lambda msg=error_msg: messagebox.showerror(
                "Error", 
                f"Error generating pivot tables:\n\n{msg}"
            ))
        
        finally:
            self.root.after(0, lambda: self.generate_btn.config(state='normal'))
            self.root.after(0, lambda: self.progress.stop())


def main():
    """Main entry point."""
    root = tk.Tk()
    app = PivotGeneratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()