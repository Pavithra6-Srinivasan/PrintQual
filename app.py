"""
app.py - Life Test Data Analysis Desktop Application

Simplified local GUI with automatic spec file detection and test type auto-detection.
"""
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime
import time
import threading

from ui_builder import create_widgets
from services.ai_service import AIService
from services.report_pipeline import ReportPipeline

class PivotGeneratorApp:
    """Desktop GUI for generating pivot tables with auto-detection."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Life Test Data Analysis")
        self.root.geometry("800x550")
        
        self.raw_data_file = tk.StringVar()
        self.output_folder = tk.StringVar(value=str(Path.cwd()))
        
        self.spec_file_path = Path.cwd() / "spec.xlsx"
        
        create_widgets(self)

        self.ai_service = AIService()
        self.latest_summary_text = None
        self.ai_thinking = False

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
        self.status_label.config(text=message, foreground=color)
        self.root.update()
    
    def generate_pivots(self):
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
        """Ask AI - works independently or with generated pivots"""
        question = self.ai_entry.get().strip()
        if not question:
            return

        self.ai_entry.delete(0, tk.END)
        self.ai_thinking = True

        # Show user question immediately
        self.ai_chat.config(state='normal')
        self.ai_chat.insert(tk.END, f"\nYou: {question}\n")
        try:
            content = self.ai_chat.get("1.0", "end")
            if "Thinking..." in content:
                lines = content.split('\n')
                new_content = '\n'.join([l for l in lines if "Thinking..." not in l])
                self.ai_chat.delete("1.0", "end")
                self.ai_chat.insert("1.0", new_content)
        except:
           pass        
        
        # Start loading animation
        self.update_status("AI thinking", "orange")
        threading.Thread(target=self.loading_animation, daemon=True).start()

        self.ai_chat.config(state='disabled')
        self.ai_chat.see(tk.END)

        thread = threading.Thread(
            target=self.ask_ai_worker,
            args=(question,),
            daemon=True
        )
        thread.start()

    def loading_animation(self):
            """Animated dots while AI is thinking"""
            dots = 0
            while self.ai_thinking:
                # Update chat with animated dots
                self.root.after(0, lambda d=dots: self.update_loading_dots(d))
                dots = (dots + 1) % 4
                time.sleep(0.5)

    def update_loading_dots(self, dots):
            """Update the loading dots in chat"""
            if not self.ai_thinking:
                return
                
            self.ai_chat.config(state='normal')
            
            # Get last line
            last_line = self.ai_chat.get("end-2l", "end-1l")
            
            # If it's the AI: line, add dots
            if last_line.startswith("AI: "):
                # Remove old dots
                self.ai_chat.delete("end-2l", "end-1l")
                # Add new dots
                dot_text = "." * dots if dots > 0 else ""
                self.ai_chat.insert("end-1l", f"AI: {dot_text}\n")
            
            self.ai_chat.config(state='disabled')
            self.ai_chat.see(tk.END)

    def ask_ai_worker(self, question):
        """Background worker for AI processing"""
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
            self.root.after(0, lambda: self.display_ai_response(response))            
            self.root.after(0, lambda: self.update_status("Ready", "green"))
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.update_status("AI Error", "red"))
            self.root.after(0, lambda msg=error_msg: self.display_ai_error(msg))
        
        finally:
            self.ai_thinking = False

    def display_ai_response(self, response):
        """Display AI chat response in clean chat format."""

        self.ai_chat.config(state='normal')

        try:
            last_line = self.ai_chat.get("end-2l", "end-1l").strip()
            if "Thinking..." in last_line:
                self.ai_chat.delete("end-2l", "end-1l")
        except Exception as e:
            print(f"Display error: {e}")

        self.ai_chat.insert(tk.END, f"{response}\n")

        self.ai_chat.config(state='disabled')
        self.ai_chat.see(tk.END)

    def display_ai_error(self, error_msg):
        """Display AI error in chat"""
        self.ai_chat.config(state='normal')
        
        # Remove loading dots
        last_line = self.ai_chat.get("end-2l", "end-1l")
        if last_line.startswith("AI: "):
            self.ai_chat.delete("end-2l", "end-1l")
        
        # Show error
        self.ai_chat.insert(tk.END, f"AI: ❌ Error: {error_msg}\n")
        self.ai_chat.insert(tk.END, "Try asking a simpler question or check that Ollama is running.\n")
        self.ai_chat.config(state='disabled')
        self.ai_chat.see(tk.END)

    def generate_worker(self):

        try:

            self.update_status("Starting generation...", "blue")

            raw_file = self.raw_data_file.get()
            spec_file = str(self.spec_file_path) if self.spec_file_path.exists() else None

            pipeline = ReportPipeline()

            result = pipeline.run(
                raw_file=raw_file,
                spec_file=spec_file,
                output_folder=self.output_folder.get()
            )

            self.latest_summary_text = result["summary_text"]

            self.log(f"Printer: {result['printer']} {result['variant']}")
            self.log(f"Sub-Assembly: {result['sub_assembly']}")
            self.log(f"Report saved: {result['output_path']}")

            self.update_status("Complete! ✓", "green")

        except Exception as e:

            import traceback

            self.log(traceback.format_exc())

            self.update_status("Error! ✗", "red")

            self.root.after(
                0,
                lambda: messagebox.showerror("Error", str(e))
            )

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