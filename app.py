"""
app.py - MODERN CHAT-LIKE INTERFACE

ChatGPT-style expanding conversation area
"""
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime
import threading

from ui_builder import create_widgets
from services.ai_service import AIService
from services.report_pipeline import ReportPipeline
from utils.paths import default_spec_path

class PivotGeneratorApp:
    """Desktop GUI with modern chat interface."""

    def __init__(self, root):
        self.root = root
        self.root.title("Life Test Data Analysis")
        self.root.geometry("900x700")  # Taller window

        self.raw_data_file = tk.StringVar()
        self.output_folder = tk.StringVar(value="")

        self.spec_file_path = default_spec_path()
        
        create_widgets(self)

        self.ai_service = AIService()
        self.latest_summary_text = None
        self.ai_thinking = False
        
        # Welcome message
        self.log_styled("Welcome!", "system")

    def browse_raw_data(self):
        """Browse for raw data file."""
        filename = filedialog.askopenfilename(
            title="Select Raw Data File",
            filetypes=[
                ("Excel files", "*.xlsx *.xlsm *.xls *.xlsb"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.raw_data_file.set(filename)
            self.log_styled(f"Selected: {Path(filename).name}", "system")
    
    def browse_output_folder(self):
        """Browse for output folder."""
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder.set(folder)
            self.log_styled(f"Output folder: {folder}", "system")
    
    def log(self, message):
        """Add system message to chat."""
        self.log_styled(message, "system")
    
    def log_styled(self, message, tag="system"):
        """Add styled message to chat."""
        self.ai_chat.config(state='normal')
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if tag == "system":
            self.ai_chat.insert(tk.END, f"[{timestamp}] ", "system")
            self.ai_chat.insert(tk.END, f"{message}\n")
        elif tag == "user":
            self.ai_chat.insert(tk.END, f"\n💬 You ({timestamp}):\n", "user")
            self.ai_chat.insert(tk.END, f"{message}\n")
        elif tag == "ai":
            self.ai_chat.insert(tk.END, f"\n🤖 AI ({timestamp}):\n", "ai")
            self.ai_chat.insert(tk.END, f"{message}\n")
        elif tag == "error":
            self.ai_chat.insert(tk.END, f"❌ Error: ", "error")
            self.ai_chat.insert(tk.END, f"{message}\n")
        
        self.ai_chat.see(tk.END)
        self.ai_chat.config(state='disabled')
        self.root.update()
    
    def update_status(self, message, color="blue"):
        color_map = {
            "blue": "#0066cc",
            "green": "#16a34a",
            "red": "#dc2626",
            "orange": "#ea580c"
        }
        self.status_label.config(text=message, foreground=color_map.get(color, color))
        self.root.update()
    
    def _validate_raw_file(self):
        if not self.raw_data_file.get():
            messagebox.showerror("Error", "Please select a raw data file!")
            return False
        if not Path(self.raw_data_file.get()).exists():
            messagebox.showerror("Error", "Raw data file does not exist!")
            return False
        return True

    def generate_pivots(self):
        if not self._validate_raw_file():
            return
        self._lock_buttons()
        threading.Thread(
            target=self._spec_check_then_generate,
            args=([], []),
            daemon=True
        ).start()

    def filter_and_generate_pivots(self):
        if not self._validate_raw_file():
            return
        self._lock_buttons()
        self.update_status("Reading data...", "blue")
        threading.Thread(target=self._read_then_show_dialog, daemon=True).start()

    def _read_then_show_dialog(self):
        try:
            from core.exclusion_filter import read_unique_values
            units, media_names = read_unique_values(self.raw_data_file.get())
            self.root.after(0, lambda: self._show_exclusion_dialog(units, media_names))
        except Exception as e:
            self.root.after(0, self._unlock_buttons)
            self.root.after(0, lambda: self.update_status("Ready", "green"))
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))

    def _show_exclusion_dialog(self, units, media_names):
        from ui_exclusion_dialog import ExclusionDialog
        self.progress.stop()
        self.update_status("Ready", "green")
        dlg = ExclusionDialog(self.root, units, media_names)
        if dlg.result is None:
            self._unlock_buttons()
            return
        excluded_units, excluded_media = dlg.result
        self.progress.start()
        self.update_status("Checking spec...", "blue")
        threading.Thread(
            target=self._spec_check_then_generate,
            args=(excluded_units, excluded_media),
            daemon=True
        ).start()

    def _lock_buttons(self):
        self.generate_btn.config(state='disabled')
        self.filter_btn.config(state='disabled')
        self.progress.start()

    def _unlock_buttons(self):
        self.generate_btn.config(state='normal')
        self.filter_btn.config(state='normal')
        self.progress.stop()
    
    def ask_ai(self):
        """Send question to AI."""
        question = self.ai_entry.get().strip()
        if not question:
            return

        self.ai_entry.delete(0, tk.END)
        self.ai_thinking = True

        # Show user question
        self.log_styled(question, "user")
        
        # Show thinking indicator
        self.ai_chat.config(state='normal')
        self.ai_chat.insert(tk.END, "\n🤖 AI: ", "ai")
        self.ai_chat.insert(tk.END, "thinking...\n")
        self.ai_chat.see(tk.END)
        self.ai_chat.config(state='disabled')
        
        self.update_status("AI thinking...", "orange")

        thread = threading.Thread(
            target=self.ask_ai_worker,
            args=(question,),
            daemon=True
        )
        thread.start()

    def ask_ai_worker(self, question):
        """Background worker for AI processing."""
        try:
            # Detect question type
            trend_keywords = ['quarter', 'trend', 'compare', 'history', 'over time', 'across']
            is_trend_question = any(kw in question.lower() for kw in trend_keywords)
            
            # Route to appropriate AI method
            if is_trend_question:
                response = self.ai_service.analyze_trends(question)
            elif self.latest_summary_text:
                response = self.ai_service.analyze_with_context(question, self.latest_summary_text)
            else:
                response = self.ai_service.answer_question(question)
            
            # Display response
            self.root.after(0, lambda r=response: self.display_ai_response(r))
            self.root.after(0, lambda: self.update_status("Ready", "green"))
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda msg=error_msg: self.display_ai_error(msg))
            self.root.after(0, lambda: self.update_status("AI Error", "red"))
        
        finally:
            self.ai_thinking = False

    def display_ai_response(self, response):
        """Display AI response."""
        self.ai_chat.config(state='normal')
        
        # Remove "thinking..." line
        content = self.ai_chat.get("1.0", tk.END)
        if "thinking..." in content:
            # Find and remove the thinking line
            lines = content.split('\n')
            new_lines = [l for l in lines if "thinking..." not in l]
            self.ai_chat.delete("1.0", tk.END)
            self.ai_chat.insert("1.0", '\n'.join(new_lines))
        
        # Add actual response
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.ai_chat.insert(tk.END, f"\n🤖 AI ({timestamp}):\n", "ai")
        self.ai_chat.insert(tk.END, f"{response}\n")
        
        self.ai_chat.see(tk.END)
        self.ai_chat.config(state='disabled')

    def display_ai_error(self, error_msg):
        """Display AI error."""
        self.ai_chat.config(state='normal')
        
        # Remove "thinking..." line
        content = self.ai_chat.get("1.0", tk.END)
        if "thinking..." in content:
            lines = content.split('\n')
            new_lines = [l for l in lines if "thinking..." not in l]
            self.ai_chat.delete("1.0", tk.END)
            self.ai_chat.insert("1.0", '\n'.join(new_lines))
        
        # Show error
        self.ai_chat.insert(tk.END, "❌ Error: ", "error")
        self.ai_chat.insert(tk.END, f"{error_msg}\n")
        self.ai_chat.insert(tk.END, "Try asking a simpler question.\n")
        
        self.ai_chat.see(tk.END)
        self.ai_chat.config(state='disabled')

    def _spec_check_then_generate(self, excluded_units, excluded_media):
        """Background thread: run spec coverage check, then show warning or proceed."""
        issues = []
        try:
            spec_file = str(self.spec_file_path) if self.spec_file_path.exists() else None
            if spec_file:
                from core.spec_checker import check_spec_coverage
                issues = check_spec_coverage(self.raw_data_file.get(), spec_file)
        except Exception as e:
            print(f"⚠ Spec check failed (proceeding anyway): {e}")

        if issues:
            self.root.after(0, lambda: self._show_spec_warning(issues, excluded_units, excluded_media))
        else:
            self.root.after(0, lambda: self.update_status("Generating...", "blue"))
            self.generate_worker(excluded_units, excluded_media)

    def _show_spec_warning(self, issues, excluded_units, excluded_media):
        """Main thread: show spec warning dialog, then route to generate or cancel."""
        from ui_spec_warning_dialog import SpecWarningDialog
        self.progress.stop()
        dlg = SpecWarningDialog(self.root, issues)
        if dlg.result:
            self.progress.start()
            self.update_status("Generating...", "blue")
            threading.Thread(
                target=self.generate_worker,
                args=(excluded_units, excluded_media),
                daemon=True
            ).start()
        else:
            self._unlock_buttons()
            self.update_status("Ready", "green")

    def generate_worker(self, excluded_units, excluded_media_names):
        """Background worker for report generation."""
        try:
            self.update_status("Generating...", "blue")

            raw_file  = self.raw_data_file.get()
            spec_file = str(self.spec_file_path) if self.spec_file_path.exists() else None

            pipeline = ReportPipeline()
            results  = pipeline.run(
                raw_file=raw_file,
                spec_file=spec_file,
                output_folder=self.output_folder.get(),
                excluded_units=excluded_units or [],
                excluded_media_names=excluded_media_names or []
            )

            # pipeline always returns a list; log each result
            for result in results:
                self.latest_summary_text = result["summary_text"]
                label = result.get("mode_label") or result.get("sub_assembly", "")
                prefix = f"[{label}] " if label else ""
                self.log(f"✓ {prefix}Printer: {result['printer']} {result['variant']}")
                self.log(f"✓ {prefix}Sub-Assembly: {result['sub_assembly']}")
                self.log(f"✓ {prefix}Quarter: Q{result['quarter']} FY{result['year']}")
                self.log(f"✓ {prefix}Excel saved: {Path(result['output_path']).name}")
                if result.get("pptx_path"):
                    self.log(f"✓ {prefix}PowerPoint saved: {Path(result['pptx_path']).name}")
                else:
                    self.log_styled(f"⚠ {prefix}PowerPoint generation failed — check console", "error")

            self.update_status("Complete! ✓", "green")
 
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            error_msg   = str(e)
            self.log_styled(error_msg, "error")
            print(error_trace)
            self.update_status("Error! ✗", "red")
            self.root.after(0, lambda msg=error_msg: messagebox.showerror("Error", msg))
 
        finally:
            self.root.after(0, self._unlock_buttons)

def main():
    """Main entry point."""
    root = tk.Tk()
    app = PivotGeneratorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()