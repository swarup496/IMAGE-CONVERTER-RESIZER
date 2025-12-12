import threading
import os
from pathlib import Path
from tkinter import (
    Tk, Button, Label, Entry, StringVar, IntVar, BooleanVar,
    filedialog, messagebox, ttk, HORIZONTAL
)
import tkinter as tk
from PIL import Image, UnidentifiedImageError

SUPPORTED_FORMATS = ("PNG", "JPEG", "JPG", "WEBP", "BMP", "TIFF")

class ImageTool:
    def __init__(self, root):
        self.root = root
        root.title("Image Converter & Resizer")
        root.geometry("720x420")
        root.resizable(False, False)

        # State variables
        self.src_paths = []
        self.output_dir = StringVar(value=str(Path.cwd() / "output_images"))
        self.format_var = StringVar(value="JPEG")
        self.quality = IntVar(value=85)
        self.keep_aspect = BooleanVar(value=True)
        self.width_var = StringVar(value="")
        self.height_var = StringVar(value="")
        self.scale_var = StringVar(value="")  # percentage e.g. 50
        self.overwrite = BooleanVar(value=False)

        self._build_ui()

    def _build_ui(self):
        padx = 10
        pady = 6

        # File selection
        Button(self.root, text="Select Files", command=self.select_files).place(x=12, y=12, width=140)
        Button(self.root, text="Select Folder", command=self.select_folder).place(x=162, y=12, width=140)
        Button(self.root, text="Clear List", command=self.clear_list).place(x=312, y=12, width=100)

        Label(self.root, text="Selected: ").place(x=12, y=52)
        self.selected_label = Label(self.root, text="0 files", anchor="w")
        self.selected_label.place(x=80, y=52, width=620)

        # Options frame
        Label(self.root, text="Output folder:").place(x=12, y=84)
        Entry(self.root, textvariable=self.output_dir).place(x=110, y=84, width=420)
        Button(self.root, text="Browse", command=self.browse_output).place(x=540, y=84, width=80)

        Label(self.root, text="Format:").place(x=12, y=120)
        formats = ["JPEG", "PNG", "WEBP", "BMP", "TIFF"]
        ttk.Combobox(self.root, values=formats, textvariable=self.format_var, state="readonly").place(x=70, y=120, width=120)

        Label(self.root, text="Quality (1-100):").place(x=210, y=120)
        Entry(self.root, textvariable=self.quality).place(x=320, y=120, width=60)

        Label(self.root, text="Resize (px):").place(x=12, y=160)
        Entry(self.root, textvariable=self.width_var).place(x=100, y=160, width=80)
        Label(self.root, text="x").place(x=187, y=160)
        Entry(self.root, textvariable=self.height_var).place(x=195, y=160, width=80)

        Label(self.root, text="or Scale %:").place(x=295, y=160)
        Entry(self.root, textvariable=self.scale_var).place(x=365, y=160, width=80)

        ttk.Checkbutton(self.root, text="Keep Aspect Ratio", variable=self.keep_aspect).place(x=470, y=158)
        ttk.Checkbutton(self.root, text="Overwrite Originals", variable=self.overwrite).place(x=620, y=158)

        # Actions
        Button(self.root, text="Start Processing", command=self.start_processing, bg="#4CAF50", fg="white").place(x=12, y=200, width=200)
        Button(self.root, text="Show Log", command=self.show_log).place(x=230, y=200, width=100)

        # Progress bar and status
        self.progress = ttk.Progressbar(self.root, orient=HORIZONTAL, length=560, mode='determinate')
        self.progress.place(x=12, y=250)
        self.status_label = Label(self.root, text="Idle", anchor="w")
        self.status_label.place(x=12, y=280, width=700)

        # Simple treeview listing files
        self.tree = ttk.Treeview(self.root, columns=("path", "size"), show='headings', height=8)
        self.tree.heading('path', text='Path')
        self.tree.heading('size', text='Size (KB)')
        self.tree.column('path', width=540)
        self.tree.column('size', width=140, anchor='center')
        self.tree.place(x=12, y=310)

        # Log storage
        self._log_lines = []

    # File/folder handling
    def select_files(self):
        files = filedialog.askopenfilenames(title="Select images", filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.webp *.tiff *.gif" )])
        if files:
            self._add_paths(list(files))

    def select_folder(self):
        folder = filedialog.askdirectory(title="Select folder containing images")
        if folder:
            # Walk folder and collect supported images
            paths = []
            for ext in ("*.png","*.jpg","*.jpeg","*.bmp","*.webp","*.tiff","*.gif"):
                paths.extend(Path(folder).rglob(ext))
            paths = [str(p) for p in paths]
            if paths:
                self._add_paths(paths)
            else:
                messagebox.showinfo("No images", "No supported images found in that folder.")

    def _add_paths(self, paths):
        added = 0
        for p in paths:
            if p not in self.src_paths:
                self.src_paths.append(p)
                size_kb = round(os.path.getsize(p)/1024)
                self.tree.insert('', 'end', values=(p, size_kb))
                added += 1
        self.selected_label.config(text=f"{len(self.src_paths)} files")
        self._log(f"Added {added} files")

    def clear_list(self):
        self.src_paths = []
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.selected_label.config(text="0 files")
        self._log("Cleared file list")

    def browse_output(self):
        d = filedialog.askdirectory(title="Choose output folder")
        if d:
            self.output_dir.set(d)

    # Processing
    def start_processing(self):
        if not self.src_paths:
            messagebox.showwarning("No files", "Please select files or a folder first.")
            return
        try:
            q = int(self.quality.get())
            if q < 1 or q > 100:
                raise ValueError
        except Exception:
            messagebox.showerror("Quality error", "Quality must be an integer between 1 and 100.")
            return

        # Disable widgets that support the 'state' option while running
        for child in self.root.winfo_children():
            try:
                child.configure(state='disabled')
            except Exception:
                pass
        threading.Thread(target=self._process_images, daemon=True).start()

    def _process_images(self):
        total = len(self.src_paths)
        self.progress['maximum'] = total
        out_dir = Path(self.output_dir.get())
        out_dir.mkdir(parents=True, exist_ok=True)

        processed = 0
        failures = 0
        for src in self.src_paths:
            try:
                self.status_label.config(text=f"Processing: {src}")
                self._process_single(Path(src), out_dir)
                processed += 1
                self._log(f"Processed: {src}")
            except Exception as e:
                failures += 1
                self._log(f"Failed: {src} -> {e}")
            self.progress['value'] = processed + failures
        self.status_label.config(text=f"Done. Processed {processed}/{total} (failed {failures})")
        self._log(f"Finished - processed {processed}/{total}, failed {failures}")

        # Re-enable widgets that support the 'state' option
        for child in self.root.winfo_children():
            try:
                child.configure(state='normal')
            except Exception:
                pass

    def _process_single(self, src_path: Path, out_dir: Path):
        # Open image
        try:
            with Image.open(src_path) as im:
                original_mode = im.mode
                # Compute target size
                target_size = self._compute_target_size(im.size)
                if target_size:
                    im = im.resize(target_size, Image.LANCZOS)

                target_format = self.format_var.get().upper()
                ext = target_format.lower()
                if ext == 'jpeg':
                    ext = 'jpg'

                # Determine output path
                if self.overwrite.get():
                    out_path = src_path.with_suffix('.' + ext)
                else:
                    out_name = src_path.stem + '.' + ext
                    out_path = out_dir / out_name

                save_kwargs = {}
                if target_format in ('JPEG', 'JPG'):
                    save_kwargs['quality'] = int(self.quality.get())
                    save_kwargs['optimize'] = True
                    # Handle alpha channel -> paste on white background
                    if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):
                        bg = Image.new('RGB', im.size, (255,255,255))
                        bg.paste(im, mask=im.split()[-1])
                        im = bg
                    else:
                        im = im.convert('RGB')

                elif target_format == 'WEBP':
                    save_kwargs['quality'] = int(self.quality.get())

                # Ensure parent exists
                out_path.parent.mkdir(parents=True, exist_ok=True)

                # Save
                im.save(out_path, target_format, **save_kwargs)

        except UnidentifiedImageError:
            raise RuntimeError("Unsupported or corrupted image")

    def _compute_target_size(self, original_size):
        ow, oh = original_size
        # If scale given, use it
        scale = None
        try:
            if self.scale_var.get().strip():
                s = float(self.scale_var.get())
                if s <= 0:
                    raise ValueError
                scale = s / 100.0
        except Exception:
            raise RuntimeError("Scale must be a positive number (percentage)")

        if scale is not None:
            return (max(1, int(ow*scale)), max(1, int(oh*scale)))

        w_text = self.width_var.get().strip()
        h_text = self.height_var.get().strip()
        if not w_text and not h_text:
            return None

        try:
            w = int(w_text) if w_text else None
            h = int(h_text) if h_text else None
        except Exception:
            raise RuntimeError("Width and Height must be integers")

        if self.keep_aspect.get():
            if w and not h:
                h = int(round((w / ow) * oh))
            elif h and not w:
                w = int(round((h / oh) * ow))
            elif w and h:
                # choose based on limiting dimension to preserve aspect
                aspect = ow/oh
                if (w/ h) > aspect:
                    # requested is wider than original -> limit by height
                    w = int(round(h * aspect))
                else:
                    h = int(round(w / aspect))
        else:
            if not w:
                w = ow
            if not h:
                h = oh

        return (max(1, w), max(1, h))

    def show_log(self):
        if not self._log_lines:
            messagebox.showinfo("Log", "No log yet.")
            return
        LOG_WIN = Tk()
        LOG_WIN.title("Log")
        txt = "\n".join(self._log_lines[-500:])
        lbl = Label(LOG_WIN, text=txt, justify='left', anchor='w')
        lbl.pack()

    def _log(self, s: str):
        self._log_lines.append(s)
        print(s)


if __name__ == '__main__':
    root = Tk()
    app = ImageTool(root)
    root.mainloop()
