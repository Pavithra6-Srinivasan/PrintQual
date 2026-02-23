"""
app_local.py - Life Test Data Analysis Desktop Application

Simplified local GUI with automatic spec file detection and test type auto-detection.
"""
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime
import threading
import urllib.parse

from services.summary_service import SummaryService
from ui_builder import create_widgets
from core.Spec_Category_config import Paperpath_CATEGORIES, ADF_CATEGORIES
from engine.database_manager import DatabaseManager
from services.pivot_service import PivotService
from services.storage_service import StorageService
from services.llm_service import LLMService

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
        create_widgets(self)

        # Load LLaMA model once
        self.llm_service = LLMService()
        self.latest_summary_text = None
        
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
        thread = threading.Thread(target=self.generate_worker, daemon=True)
        thread.start()
    
    def ask_ai(self):
        if not self.latest_summary_text:
            messagebox.showerror("Error", "Generate pivots first!")
            return

        question = self.ai_entry.get().strip()
        if not question:
            return

        self.ai_entry.delete(0, tk.END)

        system_prompt = """
    You are a senior quality data analyst.
    Analyze pivot summary results and provide professional insights.
    Be clear, structured and concise.
    """

        full_prompt = f"""
    User Question:
    {question}

    Pivot Summary:
    {self.latest_summary_text}
    """

        response = self.llm_service.ask(system_prompt, full_prompt)

        self.ai_chat.config(state='normal')
        self.ai_chat.insert(tk.END, f"\nYou: {question}\n", "user")
        self.ai_chat.insert(tk.END, f"AI: {response}\n", "assistant")
        self.ai_chat.config(state='disabled')
        self.ai_chat.see(tk.END)

    def display_ai_summary(self, summary_text):
        """Display AI summary in chat-style format."""
        self.ai_chat.config(state='normal')
        self.ai_chat.delete("1.0", tk.END)

        formatted_text = (
            "AI Analysis Summary\n"
            "============================\n\n"
            f"{summary_text}\n"
        )

        self.ai_chat.insert(tk.END, formatted_text)
        self.ai_chat.config(state='disabled')

    def generate_worker(self):
        try:
            self.update_status("Starting generation...", "blue")
            self.log("GENERATING PIVOT TABLES")

            raw_file = self.raw_data_file.get()
            spec_file = str(self.spec_file_path) if self.spec_file_path.exists() else None

            # Detect Test Type
            pivot_service = PivotService(raw_file, spec_file)
            sub_assembly, product, sheet_name = pivot_service.detect_test_type()

            if sub_assembly.upper() == "ADF":
                test_categories = ADF_CATEGORIES
            else:
                test_categories = Paperpath_CATEGORIES

            self.log_text.config(state='normal')
            self.log_text.delete("1.0", tk.END)
            self.log_text.insert(tk.END, f"Printer: {product}\n")
            self.log_text.insert(tk.END, f"Sub-Assembly: {sub_assembly}\n")
            self.log_text.config(state='disabled')

            # Generate All Pivots Once
            self.update_status("Generating pivots...", "blue")
            all_pivots = pivot_service.generate_all_pivots(test_categories)

            # Save Excel
            self.update_status("Saving Excel...", "blue")

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"{product}_{sheet_name}_Pivot_{timestamp}.xlsx"
            output_path = Path(self.output_folder.get()) / output_filename

            storage = StorageService()

            # Generate Summary
            self.update_status("Generating summary...", "blue")

            summary_service = SummaryService(all_pivots)
            summary_data, summary_text = summary_service.generate()
            self.latest_summary_text = summary_text
            self.display_ai_summary(summary_text)

            # Save to Database
            self.update_status("Saving to database...", "blue")

            db = DatabaseManager(
                host="15.46.29.115",
                database="quality_sandbox",
                username="pavithra_030226",
                password = urllib.parse.quote_plus("pavithra@030226"),
                db_type="mysql"
            )

            db.create_tables()
            db.insert_summary(summary_data)

            # Auto-generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"{product}_{sheet_name}_Pivot_Tables_{timestamp}.xlsx"
            output_path = Path(self.output_folder.get()) / output_filename
            
            storage = StorageService()
            storage.save_excel(output_path, all_pivots)

            
            self.log_text.config(state='normal')
            
            self.update_status("Complete! ✓", "green")
        
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