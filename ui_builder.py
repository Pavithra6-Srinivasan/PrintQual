"""
ui_builder.py
Handles all UI widget creation and layout for the PivotGeneratorApp.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext


def create_widgets(app):
    """Create all UI widgets and attach them to the app instance."""

    main_frame = ttk.Frame(app.root, padding="10")
    main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    app.root.columnconfigure(0, weight=1)
    app.root.rowconfigure(0, weight=1)
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
    ttk.Entry(main_frame, textvariable=app.raw_data_file, width=60).grid(
        row=row, column=1, sticky=(tk.W, tk.E), padx=5
    )
    ttk.Button(main_frame, text="Browse...", command=app.browse_raw_data).grid(
        row=row, column=2, padx=5
    )

    # Output Folder Section
    row += 1
    ttk.Label(main_frame, text="Output Folder:", font=('Arial', 10, 'bold')).grid(
        row=row, column=0, sticky=tk.W, pady=5
    )
    ttk.Entry(main_frame, textvariable=app.output_folder, width=60).grid(
        row=row, column=1, sticky=(tk.W, tk.E), padx=5
    )
    ttk.Button(main_frame, text="Browse...", command=app.browse_output_folder).grid(
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
    app.generate_btn = ttk.Button(main_frame, text="Generate Pivot Tables",
                                  command=app.generate_pivots)
    app.generate_btn.grid(row=row, column=0, columnspan=3, pady=20)

    # Progress Bar
    row += 1
    app.progress = ttk.Progressbar(main_frame, mode='indeterminate')
    app.progress.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

    # Status Label
    row += 1
    app.status_label = ttk.Label(main_frame, text="Ready", foreground="blue")
    app.status_label.grid(row=row, column=0, columnspan=3, pady=5)

    # =========================
    # Detection Summary Section
    # =========================
    row += 1
    ttk.Label(main_frame, text="Detection Summary:", 
              font=('Arial', 10, 'bold')).grid(
        row=row, column=0, sticky=tk.W, pady=(15, 5)
    )

    row += 1
    app.log_text = scrolledtext.ScrolledText(
        main_frame,
        height=4,
        wrap=tk.WORD,
        state='disabled'
    )
    app.log_text.grid(
        row=row,
        column=0,
        columnspan=3,
        sticky=(tk.W, tk.E),
        pady=5
    )

    # =========================
    # AI Assistant Section
    # =========================
    row += 1
    ttk.Label(main_frame, text="AI Assistant Summary:", 
              font=('Arial', 10, 'bold')).grid(
        row=row, column=0, sticky=tk.W, pady=(15, 5)
    )

    row += 1
    app.ai_chat = scrolledtext.ScrolledText(
        main_frame,
        height=10,
        wrap=tk.WORD,
        state='disabled'
    )
    app.ai_chat.grid(
        row=row,
        column=0,
        columnspan=3,
        sticky=(tk.W, tk.E, tk.N, tk.S),
        pady=5
    )

    # Make AI section expandable
    main_frame.rowconfigure(row, weight=1)

    # AI Chat Section
    row += 1
    ttk.Label(main_frame, text="AI Assistant:", font=('Arial', 10, 'bold')).grid(
        row=row, column=0, sticky=tk.W, pady=(15, 5)
    )

    row += 1
    app.ai_chat = scrolledtext.ScrolledText(
        main_frame, height=10, width=80,
        wrap=tk.WORD, state='disabled'
    )
    app.ai_chat.grid(row=row, column=0, columnspan=3,
                    sticky=(tk.W, tk.E), pady=5)

    row += 1
    app.ai_entry = ttk.Entry(main_frame)
    app.ai_entry.grid(row=row, column=0, columnspan=2,
                    sticky=(tk.W, tk.E), pady=5)

    ttk.Button(main_frame, text="Ask AI",
            command=app.ask_ai).grid(row=row, column=2, padx=5)

    # Instructions
    row += 1
    instructions = """
Instructions:
1. Select your raw data file (Excel format)
2. Choose output folder
3. Click \"Generate Pivot Tables\"
4. System will auto-detect test type (Paperpath/ADF)
5. Results will be saved to output folder
    """
    ttk.Label(main_frame, text=instructions, justify=tk.LEFT,
              foreground="gray").grid(row=row, column=0,
                                        columnspan=3, pady=10, sticky=tk.W)
