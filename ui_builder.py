"""
ui_builder.py - MODERN CHAT-LIKE INTERFACE

ChatGPT-style layout:
- Top: File selection and controls (compact)
- Middle: Expanding chat area (grows with content)
- Bottom: Fixed AI input bar
"""

import tkinter as tk
from tkinter import ttk, scrolledtext

def create_widgets(app):
    """Create modern chat-like UI."""
    
    # Main container
    app.root.columnconfigure(0, weight=1)
    app.root.rowconfigure(0, weight=1)
    
    main_container = ttk.Frame(app.root)
    main_container.grid(row=0, column=0, sticky="nsew")
    main_container.columnconfigure(0, weight=1)
    main_container.rowconfigure(1, weight=1)  # Chat area expands
    
    # ======================
    # TOP SECTION - Controls (Fixed Height)
    # ======================
    top_frame = ttk.Frame(main_container, padding="10")
    top_frame.grid(row=0, column=0, sticky="nsew")
    top_frame.columnconfigure(1, weight=1)
    
    # Title
    title_label = ttk.Label(
        top_frame, 
        text="Life Test Data Analysis",
        font=('Segoe UI', 16, 'bold')
    )
    title_label.grid(row=0, column=0, columnspan=3, pady=(0, 15))
    
    # Raw Data File
    ttk.Label(top_frame, text="Raw Data File:", font=('Segoe UI', 9)).grid(
        row=1, column=0, sticky=tk.W, pady=5, padx=(0, 5)
    )
    ttk.Entry(top_frame, textvariable=app.raw_data_file, width=50).grid(
        row=1, column=1, sticky="ew", padx=5
    )
    ttk.Button(top_frame, text="Browse", command=app.browse_raw_data).grid(
        row=1, column=2, padx=(5, 0)
    )
    
    # Output Folder
    ttk.Label(top_frame, text="Output Folder:", font=('Segoe UI', 9)).grid(
        row=2, column=0, sticky=tk.W, pady=5, padx=(0, 5)
    )
    ttk.Entry(top_frame, textvariable=app.output_folder, width=50).grid(
        row=2, column=1, sticky="ew", padx=5
    )
    ttk.Button(top_frame, text="Browse", command=app.browse_output_folder).grid(
        row=2, column=2, padx=(5, 0)
    )
    
    # Generate Button & Status
    button_frame = ttk.Frame(top_frame)
    button_frame.grid(row=3, column=0, columnspan=3, pady=10)
    
    app.generate_btn = ttk.Button(
        button_frame, 
        text="Generate Report",
        command=app.generate_pivots
    )
    app.generate_btn.pack(side=tk.LEFT, padx=5)
    
    app.status_label = ttk.Label(
        button_frame, 
        text="Ready", 
        foreground="green",
        font=('Segoe UI', 9, 'bold')
    )
    app.status_label.pack(side=tk.LEFT, padx=10)
    
    # Progress Bar
    app.progress = ttk.Progressbar(top_frame, mode='indeterminate')
    app.progress.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 5))
    
    # Separator
    ttk.Separator(top_frame, orient='horizontal').grid(
        row=5, column=0, columnspan=3, sticky="ew", pady=10
    )
    
    # ======================
    # MIDDLE SECTION - Chat Area (Expanding)
    # ======================
    chat_container = ttk.Frame(main_container)
    chat_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
    chat_container.columnconfigure(0, weight=1)
    chat_container.rowconfigure(0, weight=1)
    
    # Combined Chat/Log Area
    chat_frame = ttk.LabelFrame(chat_container, text="  Conversation  ", padding="5")
    chat_frame.grid(row=0, column=0, sticky="nsew")
    chat_frame.columnconfigure(0, weight=1)
    chat_frame.rowconfigure(0, weight=1)
    
    # Scrollable text area (ChatGPT style)
    app.ai_chat = scrolledtext.ScrolledText(
        chat_frame,
        wrap=tk.WORD,
        font=('Segoe UI', 10),
        bg="#f7f7f8",
        fg="#333333",
        relief=tk.FLAT,
        padx=10,
        pady=10,
        state='disabled'
    )
    app.ai_chat.grid(row=0, column=0, sticky="nsew")
    
    # Configure text tags for styling
    app.ai_chat.tag_config("user", foreground="#0066cc", font=('Segoe UI', 10, 'bold'))
    app.ai_chat.tag_config("ai", foreground="#16a34a", font=('Segoe UI', 10, 'bold'))
    app.ai_chat.tag_config("system", foreground="#6b7280", font=('Segoe UI', 9, 'italic'))
    app.ai_chat.tag_config("error", foreground="#dc2626", font=('Segoe UI', 10))
    
    # Also use this for log messages
    app.log_text = app.ai_chat  # Reuse same widget
    
    # ======================
    # BOTTOM SECTION - AI Input (Fixed)
    # ======================
    bottom_frame = ttk.Frame(main_container)
    bottom_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
    bottom_frame.columnconfigure(0, weight=1)
    
    # Input frame
    input_frame = ttk.Frame(bottom_frame, relief=tk.RAISED, borderwidth=1)
    input_frame.grid(row=0, column=0, sticky="ew")
    input_frame.columnconfigure(0, weight=1)
    
    # AI Entry
    app.ai_entry = ttk.Entry(
        input_frame,
        font=('Segoe UI', 10)
    )
    app.ai_entry.grid(row=0, column=0, sticky="ew", padx=10, pady=8)
    
    # Bind Enter key to send
    app.ai_entry.bind('<Return>', lambda e: app.ask_ai())
    
    # Ask Button
    ask_btn = ttk.Button(
        input_frame,
        text="Enter ➤",
        command=app.ask_ai
    )
    ask_btn.grid(row=0, column=1, padx=(0, 10), pady=8)
    
    # Hint text
    hint_label = ttk.Label(
        bottom_frame,
        text="💡 Ask about trends, failures, or specific test results (Press Enter to send)",
        font=('Segoe UI', 8),
        foreground="#6b7280"
    )
    hint_label.grid(row=1, column=0, pady=(5, 0))

# Helper method to add to app.py
def log_with_style(app, message, tag="system"):
    """Add styled message to chat."""
    app.ai_chat.config(state='normal')
    timestamp = __import__('datetime').datetime.now().strftime("%H:%M:%S")
    app.ai_chat.insert(tk.END, f"[{timestamp}] ", tag)
    app.ai_chat.insert(tk.END, f"{message}\n")
    app.ai_chat.see(tk.END)
    app.ai_chat.config(state='disabled')