import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import hl7_defs

class HL7ViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SmartHL7 Style Viewer")
        self.root.geometry("1200x800")

        # Config
        self.font_main = ('Segoe UI', 10)
        self.font_mono = ('Consolas', 10)

        # Use a modern theme if available
        self.style = ttk.Style()
        try:
            self.style.theme_use('clam')
        except:
            pass
        
        # Configure common styles
        self.style.configure(".", font=self.font_main)
        self.style.configure("Treeview", rowheight=25, font=self.font_main)
        self.style.configure("Treeview.Heading", font=('Segoe UI', 10, 'bold'))

        # --- Menu Bar ---
        self.menu_bar = tk.Menu(root)
        self.root.config(menu=self.menu_bar)
        
        # Theme Menu
        self.theme_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Theme", menu=self.theme_menu)
        self.theme_menu.add_command(label="Light Mode", command=lambda: self.apply_theme("light"))
        self.theme_menu.add_command(label="Dark Mode", command=lambda: self.apply_theme("dark"))

        # --- Toolbar ---
        self.toolbar = ttk.Frame(root, padding="5 5 5 5")
        self.toolbar.pack(side=tk.TOP, fill=tk.X)
        
        ttk.Button(self.toolbar, text="Clear", command=self.clear_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.toolbar, text="Paste HL7", command=self.paste_from_clipboard).pack(side=tk.LEFT, padx=5)

        # --- Main Vertical PanedWindow ---
        self.main_paned = tk.PanedWindow(root, orient=tk.VERTICAL, sashrelief=tk.FLAT, sashwidth=4, bg="#dcdad5")
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 1. Top Pane: Raw HL7 Text
        self.top_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.top_frame, height=200) # Initial height
        
        self.lbl_raw = ttk.Label(self.top_frame, text="Raw HL7 Message (Read Only - Use Paste button):", font=('Segoe UI', 9, 'bold'))
        self.lbl_raw.pack(anchor=tk.W, pady=(0, 5))
        self.text_input = scrolledtext.ScrolledText(self.top_frame, height=8, state='disabled', font=self.font_mono, bd=0, highlightthickness=1) 
        self.text_input.pack(fill=tk.BOTH, expand=True)

        # 2. Bottom Pane: Horizontal PanedWindow (Segment | Components)
        self.bottom_paned = tk.PanedWindow(self.main_paned, orient=tk.HORIZONTAL, sashrelief=tk.FLAT, sashwidth=4, bg="#dcdad5")
        self.main_paned.add(self.bottom_paned)

        # --- Left: Segment List ---
        self.seg_frame = ttk.Labelframe(self.bottom_paned, text="Segments", padding=5)
        self.bottom_paned.add(self.seg_frame, width=220)

        self.seg_tree = ttk.Treeview(self.seg_frame, columns=("index", "name"), show="headings", selectmode="browse")
        self.seg_tree.heading("index", text="#")
        self.seg_tree.column("index", width=40, anchor=tk.CENTER)
        self.seg_tree.heading("name", text="Segment")
        self.seg_tree.column("name", width=120, anchor=tk.W)
        
        seg_scroll = ttk.Scrollbar(self.seg_frame, orient="vertical", command=self.seg_tree.yview)
        self.seg_tree.configure(yscrollcommand=seg_scroll.set)
        
        self.seg_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        seg_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind select
        self.seg_tree.bind("<<TreeviewSelect>>", self.on_segment_select)

        # --- Middle: Field List ---
        self.field_frame = ttk.Labelframe(self.bottom_paned, text="Fields", padding=5)
        self.bottom_paned.add(self.field_frame, width=500)

        # Columns: Field Index, Description, Value
        self.field_tree = ttk.Treeview(self.field_frame, columns=("idx", "desc", "value"), show="headings", selectmode="browse")
        
        self.field_tree.heading("idx", text="Idx")
        self.field_tree.column("idx", width=50, anchor=tk.CENTER)
        
        self.field_tree.heading("desc", text="Description")
        self.field_tree.column("desc", width=250, anchor=tk.W)
        
        self.field_tree.heading("value", text="Value")
        self.field_tree.column("value", width=300, anchor=tk.W)

        field_scroll = ttk.Scrollbar(self.field_frame, orient="vertical", command=self.field_tree.yview)
        self.field_tree.configure(yscrollcommand=field_scroll.set)
        
        self.field_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        field_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.field_tree.bind("<<TreeviewSelect>>", self.on_field_select)
        self.field_tree.bind("<Control-c>", lambda e: self.copy_tree_selection(self.field_tree, col_idx=2))
        self.field_tree.bind("<Double-1>", lambda e: self.copy_and_alert(self.field_tree, col_idx=2))

        # --- Right: Component List (Sub-components) ---
        self.comp_frame = ttk.Labelframe(self.bottom_paned, text="Components", padding=5)
        self.bottom_paned.add(self.comp_frame, width=300)
        
        self.comp_tree = ttk.Treeview(self.comp_frame, columns=("idx", "value"), show="headings")
        self.comp_tree.heading("idx", text="#")
        self.comp_tree.column("idx", width=40, anchor=tk.CENTER)
        self.comp_tree.heading("value", text="Value")
        self.comp_tree.column("value", width=200, anchor=tk.W)
        
        self.comp_tree.pack(fill=tk.BOTH, expand=True)
        self.comp_tree.bind("<Control-c>", lambda e: self.copy_tree_selection(self.comp_tree, col_idx=1))
        self.comp_tree.bind("<Double-1>", lambda e: self.copy_and_alert(self.comp_tree, col_idx=1))

        # Data store
        self.parsed_segments = []
        
        # Apply default theme
        self.apply_theme("light")
        
        # Bind Paste (Ctrl+V) globally since text widget is disabled
        self.root.bind("<Control-v>", lambda e: self.paste_from_clipboard())

    def apply_theme(self, theme):
        if theme == 'dark':
            bg_color = '#2d2d2d' # Softer dark
            fg_color = '#e0e0e0' # Soft white
            field_bg = '#363636' # Slightly lighter dark
            select_bg = '#007acc' # GitHub/VSCode blue
            sash_bg = '#2d2d2d'
            
            # Row Colors
            even_bg = field_bg
            # Increased contrast for dark mode
            odd_bg = '#4a4a4a'  
            
            # General
            self.style.configure(".", background=bg_color, foreground=fg_color)
            
            # Treeview
            self.style.configure("Treeview", 
                                 background=field_bg, 
                                 foreground=fg_color, 
                                 fieldbackground=field_bg,
                                 borderwidth=0)
            self.style.configure("Treeview.Heading", 
                                 background='#3c3c3c', 
                                 foreground=fg_color,
                                 relief="solid", borderwidth=1) # Enable Header Borders
            self.style.map("Treeview", 
                           background=[('selected', select_bg)], 
                           foreground=[('selected', 'white')])

            # Frames
            self.style.configure("TLabelframe", background=bg_color, foreground=fg_color)
            self.style.configure("TLabelframe.Label", background=bg_color, foreground=fg_color)
            
            # Text Widget
            self.text_input.configure(bg=field_bg, fg=fg_color, insertbackground=fg_color, selectbackground=select_bg)
            
            # Panes
            self.root.configure(bg=bg_color)
            self.main_paned.configure(bg=bg_color, sashcursor="sb_v_double_arrow")
            self.bottom_paned.configure(bg=bg_color, sashcursor="sb_h_double_arrow")

        else: # Light
            bg_color = '#f5f7fa' # Very light greyish blue
            fg_color = '#333333' # Dark gray text
            field_bg = '#ffffff'
            select_bg = '#0078d4' # Windows Blue
            sash_bg = '#e1e4e8'
            
            # Row Colors
            even_bg = '#ffffff'
            # Increased contrast for light mode (more visible light gray/blue)
            odd_bg = '#e1e5eb' 

            # General
            self.style.configure(".", background=bg_color, foreground=fg_color)
            
            # Treeview
            self.style.configure("Treeview", 
                                 background=field_bg, 
                                 foreground=fg_color, 
                                 fieldbackground=field_bg,
                                 borderwidth=0)
            self.style.configure("Treeview.Heading", 
                                 background='#e1e4e8', 
                                 foreground='#333333',
                                 relief="solid", borderwidth=1) # Enable Header Borders
            self.style.map("Treeview", 
                           background=[('selected', select_bg)], 
                           foreground=[('selected', 'white')])

            # Frames
            self.style.configure("TLabelframe", background=bg_color, foreground=fg_color)
            self.style.configure("TLabelframe.Label", background=bg_color, foreground=fg_color)

            # Text Widget
            self.text_input.configure(bg="#ffffff", fg="black", insertbackground="black", selectbackground=select_bg)
            
            # Panes
            self.root.configure(bg=bg_color)
            self.main_paned.configure(bg=sash_bg)
            self.bottom_paned.configure(bg=sash_bg)

        # Configure tags for all trees to show grid lines (stripes)
        for tree in [self.seg_tree, self.field_tree, self.comp_tree]:
            tree.tag_configure('odd', background=odd_bg)
            tree.tag_configure('even', background=even_bg)

    def paste_from_clipboard(self):
        try:
            data = self.root.clipboard_get()
            self.text_input.configure(state='normal')
            self.text_input.delete("1.0", tk.END)
            self.text_input.insert("1.0", data)
            self.text_input.configure(state='disabled')
            # Auto-parse on paste?
            self.parse_message()
        except tk.TclError:
            pass # Clipboard empty or not text

    def copy_tree_selection(self, tree, col_idx):
        selected_item = tree.selection()
        if selected_item:
            # Get the values of the selected record
            vals = tree.item(selected_item[0])['values']
            if len(vals) > col_idx:
                val_to_copy = vals[col_idx]
                self.root.clipboard_clear()
                self.root.clipboard_append(str(val_to_copy))
                self.root.update() # Required to finalize clipboard copy

    def copy_and_alert(self, tree, col_idx):
        # Identify the item under the mouse to ensure we select it first if not already
        # But usually double click naturally selects it.
        # Just reuse copy logic but add alert.
        self.copy_tree_selection(tree, col_idx)
        
        # Verify if something was validly copied? 
        # For simplicity, if selection exists, we assume copy happened.
        if tree.selection():
            messagebox.showinfo("Copied", "Value copied to clipboard")

    def clear_all(self):
        self.text_input.configure(state='normal')
        self.text_input.delete("1.0", tk.END)
        self.text_input.configure(state='disabled')
        self.parsed_segments = []
        self.clear_trees()

    def clear_trees(self):
        for t in [self.seg_tree, self.field_tree, self.comp_tree]:
            for item in t.get_children():
                t.delete(item)

    def parse_message(self):
        self.parsed_segments = []
        self.clear_trees()
        
        raw_text = self.text_input.get("1.0", tk.END).strip()
        if not raw_text:
            return

        # Normalize logic
        raw_text = raw_text.replace('\r\n', '\r').replace('\n', '\r')
        segments = raw_text.split('\r')

        for i, segment_str in enumerate(segments):
            if not segment_str.strip():
                continue
            
            parts = segment_str.split('|')
            seg_name = parts[0]
            
            # Construct standard fields list
            # Handle MSH special case: Field 1 is '|', Field 2 is '^~\&'
            if seg_name == 'MSH':
                # MSH|^~\&|...
                # parts[0] = MSH
                # parts[1] = ^~\& (This is technically MSH.2)
                # MSH.1 is the separator '|'
                fields = ['|'] + parts[1:] # Shift everything by 1, and insert separator as first field
            else:
                # Ordinary segment: PID|1|...
                # parts[0] = PID
                # parts[1] = Field 1
                fields = parts[1:]

            self.parsed_segments.append({
                'name': seg_name,
                'raw': segment_str,
                'fields': fields
            })
            
            # Add to Segment Tree
            tag = 'odd' if i % 2 else 'even'
            self.seg_tree.insert("", tk.END, iid=str(i), values=(i+1, seg_name), tags=(tag,))

    def on_segment_select(self, event):
        selected_items = self.seg_tree.selection()
        if not selected_items:
            return
        
        # Clear details
        for item in self.field_tree.get_children(): 
            self.field_tree.delete(item)
        for item in self.comp_tree.get_children(): 
            self.comp_tree.delete(item)

        idx = int(selected_items[0]) # The IID is the index
        if idx >= len(self.parsed_segments): 
            return

        seg_data = self.parsed_segments[idx]
        seg_name = seg_data['name']
        fields = seg_data['fields']
        
        # Populate Fields
        for i, val in enumerate(fields):
            field_idx = i + 1
            desc = self.get_field_name(seg_name, field_idx)
            
            # Insert into tree
            # iid = "segIdx_fieldIdx"
            tag = 'odd' if i % 2 else 'even'
            self.field_tree.insert("", tk.END, iid=f"{idx}_{i}", values=(field_idx, desc, val), tags=(tag,))

    def on_field_select(self, event):
        selected_items = self.field_tree.selection()
        if not selected_items:
            return
        
        for item in self.comp_tree.get_children():
            self.comp_tree.delete(item)
            
        # iid format: "segIdx_fieldIdx"
        iid = selected_items[0]
        seg_idx, field_idx_0 = map(int, iid.split('_'))
        
        val = self.parsed_segments[seg_idx]['fields'][field_idx_0]
        
        # Split by component separator '^'
        if '^' in val:
            comps = val.split('^')
            for i, c_val in enumerate(comps):
                tag = 'odd' if i % 2 else 'even'
                self.comp_tree.insert("", tk.END, values=(i+1, c_val), tags=(tag,))
        else:
            self.comp_tree.insert("", tk.END, values=(1, val), tags=('odd',)) # Single item odd

    def get_field_name(self, segment, index):
        if segment in hl7_defs.HL7_SEGMENTS:
            return hl7_defs.HL7_SEGMENTS[segment].get(index, "")
        return ""
