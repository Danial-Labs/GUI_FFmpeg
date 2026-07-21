"""
main.py
Video Shrinker - a friendly desktop GUI for compressing videos with ffmpeg.

Run:
    pip install -r requirements.txt
    python main.py
"""

import os
import threading
import subprocess
import platform
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

import ffmpeg_manager
import compressor

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

APP_TITLE = "GUI_FFmpeg"
AUTHOR_LINK = "https://t.me/DanialLabs"

# ---- palette ----
ACCENT = "#7C6FF0"
ACCENT_HOVER = "#665adf"
ACCENT_SOFT = ("#eceaff", "#242038")
SUCCESS = "#2ecc91"
SUCCESS_HOVER = "#25b07d"
DANGER = "#ff5c5c"
MUTED = "#8b8fa3"
WINDOW_BG = ("#eef0f6", "#101018")
CARD_BG = ("#ffffff", "#1a1a26")
BORDER = ("#e2e4ee", "#2a2a3a")

FONT_TITLE = ("Segoe UI", 24, "bold")
FONT_SECTION = ("Segoe UI", 14, "bold")
FONT_BODY = ("Segoe UI", 13)
FONT_SMALL = ("Segoe UI", 11)


def open_in_file_manager(path: str):
    try:
        if platform.system() == "Windows":
            os.startfile(path)  # noqa
        elif platform.system() == "Darwin":
            subprocess.run(["open", path])
        else:
            subprocess.run(["xdg-open", path])
    except Exception:
        pass


def section_title(parent, icon, text):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    bar = ctk.CTkFrame(row, width=4, height=18, corner_radius=2, fg_color=ACCENT)
    bar.pack(side="left", padx=(0, 8))
    label = ctk.CTkLabel(row, text=f"{icon}  {text}", font=FONT_SECTION, anchor="w")
    label.pack(side="left")
    return row


class SetupFrame(ctk.CTkFrame):
    """First screen: check for / install ffmpeg automatically."""

    def __init__(self, master, on_ready):
        super().__init__(master, fg_color=WINDOW_BG)
        self.on_ready = on_ready

        container = ctk.CTkFrame(self, corner_radius=26, fg_color=CARD_BG,
                                  border_width=1, border_color=BORDER)
        container.place(relx=0.5, rely=0.5, anchor="center")

        inner = ctk.CTkFrame(container, fg_color="transparent")
        inner.pack(padx=52, pady=48)

        badge = ctk.CTkFrame(inner, width=88, height=88, corner_radius=24, fg_color=ACCENT_SOFT)
        badge.pack(pady=(0, 18))
        badge.pack_propagate(False)
        ctk.CTkLabel(badge, text="🎬", font=("Segoe UI", 40)).pack(expand=True)

        ctk.CTkLabel(inner, text="Welcome to GUI_FFmpeg",
                     font=FONT_TITLE).pack(pady=(0, 6))

        ctk.CTkLabel(
            inner,
            text="Before you start, ffmpeg needs to be available on this system.\n"
                 "If it's already installed, we'll detect it automatically.",
            font=FONT_BODY, text_color=MUTED, justify="center",
        ).pack(pady=(0, 18))

        credit = ctk.CTkLabel(
            inner, text=f"by {AUTHOR_LINK}", font=FONT_SMALL, text_color=ACCENT, cursor="hand2",
        )
        credit.pack(pady=(0, 26))
        credit.bind("<Button-1>", lambda e: webbrowser.open(AUTHOR_LINK))

        self.status_label = ctk.CTkLabel(inner, text="", font=FONT_BODY)
        self.status_label.pack(pady=(0, 10))

        self.progress = ctk.CTkProgressBar(inner, width=360, height=14, corner_radius=8,
                                            progress_color=ACCENT)
        self.progress.set(0)
        self.progress.pack(pady=(0, 22))
        self.progress.pack_forget()

        self.action_btn = ctk.CTkButton(
            inner, text="Check system & continue", width=280, height=50, corner_radius=16,
            font=("Segoe UI", 15, "bold"), fg_color=ACCENT, hover_color=ACCENT_HOVER,
            command=self.start_check,
        )
        self.action_btn.pack()

        self.after(200, self.start_check)

    def start_check(self):
        self.action_btn.configure(state="disabled", text="Checking...")
        self.status_label.configure(text="")
        threading.Thread(target=self._check_worker, daemon=True).start()

    def _check_worker(self):
        if ffmpeg_manager.is_ffmpeg_available():
            self.after(0, self._on_already_available)
        else:
            self.after(0, self._show_install_prompt)

    def _on_already_available(self):
        self.status_label.configure(text="ffmpeg was found on your system", text_color=SUCCESS)
        self.action_btn.configure(text="Enter the app", state="normal", command=self._finish)
        self.after(700, self._finish)

    def _show_install_prompt(self):
        self.status_label.configure(
            text="ffmpeg was not found. Click below to download and install it automatically.",
            text_color=MUTED,
        )
        self.action_btn.configure(
            text="Download & install ffmpeg", state="normal", command=self.start_install
        )

    def start_install(self):
        self.action_btn.configure(state="disabled", text="Installing...")
        self.progress.pack(pady=(0, 22))
        self.progress.set(0)
        threading.Thread(target=self._install_worker, daemon=True).start()

    def _install_worker(self):
        try:
            def on_status(msg):
                self.after(0, lambda: self.status_label.configure(text=msg, text_color=MUTED))

            def on_progress(frac):
                self.after(0, lambda: self.progress.set(frac))

            ffmpeg_manager.download_and_install(on_status, on_progress)
            self.after(0, self._on_install_done)
        except Exception as exc:
            self.after(0, lambda: self._on_install_failed(str(exc)))

    def _on_install_done(self):
        self.status_label.configure(text="Installed successfully", text_color=SUCCESS)
        self.action_btn.configure(text="Enter the app", state="normal", command=self._finish)
        self.after(700, self._finish)

    def _on_install_failed(self, msg):
        self.progress.pack_forget()
        self.status_label.configure(text=f"Install failed: {msg}", text_color=DANGER)
        self.action_btn.configure(text="Try again", state="normal", command=self.start_install)

    def _finish(self):
        self.on_ready()


class MainFrame(ctk.CTkFrame):
    """Main screen: pick a video and configure compression."""

    def __init__(self, master):
        super().__init__(master, fg_color=WINDOW_BG)

        self.ffmpeg_path, self.ffprobe_path = ffmpeg_manager.find_ffmpeg()
        self.video_path = None
        self.video_info = None
        self.custom_output_path = None
        self.is_running = False

        self._build_ui()

    # ---------------- layout ----------------

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ---- header bar ----
        header = ctk.CTkFrame(self, fg_color="transparent", height=70)
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 8))
        header.grid_columnconfigure(1, weight=1)

        badge = ctk.CTkFrame(header, width=44, height=44, corner_radius=14, fg_color=ACCENT_SOFT)
        badge.grid(row=0, column=0, padx=(0, 12))
        badge.grid_propagate(False)
        ctk.CTkLabel(badge, text="🎬", font=("Segoe UI", 20)).place(relx=0.5, rely=0.5, anchor="center")

        title_col = ctk.CTkFrame(header, fg_color="transparent")
        title_col.grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(title_col, text="GUI_FFmpeg", font=FONT_TITLE, anchor="w").pack(anchor="w")

        credit = ctk.CTkLabel(
            title_col, text=f"by {AUTHOR_LINK}", font=FONT_SMALL, text_color=MUTED,
            cursor="hand2", anchor="w",
        )
        credit.pack(anchor="w")
        credit.bind("<Button-1>", lambda e: webbrowser.open(AUTHOR_LINK))

        self.theme_switch = ctk.CTkSegmentedButton(
            header, values=["Light", "Dark"], command=self._toggle_theme, width=130,
            selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
        )
        self.theme_switch.set("Dark")
        self.theme_switch.grid(row=0, column=2, sticky="e")

        # ---- scrollable body ----
        self.scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=ACCENT, scrollbar_button_hover_color=ACCENT_HOVER,
        )
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 20))
        self.scroll.grid_columnconfigure(0, weight=1)

        self._build_file_card()
        self._build_mode_card()
        self._build_output_card()
        self._build_action_card()

    def _card(self, **kwargs):
        card = ctk.CTkFrame(self.scroll, corner_radius=20, fg_color=CARD_BG,
                             border_width=1, border_color=BORDER)
        card.grid(sticky="ew", pady=(0, 16), **kwargs)
        card.grid_columnconfigure(0, weight=1)
        return card

    def _build_file_card(self):
        card = self._card(row=0, column=0)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=26, pady=22)
        inner.grid_columnconfigure(0, weight=1)

        section_title(inner, "📁", "Source video").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))

        self.file_label = ctk.CTkLabel(
            inner, text="No video selected yet", font=FONT_BODY, text_color=MUTED, anchor="w"
        )
        self.file_label.grid(row=1, column=0, sticky="ew", padx=(0, 12))

        ctk.CTkButton(
            inner, text="Browse...", width=140, height=42, corner_radius=14,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, command=self.pick_file,
        ).grid(row=1, column=1)

        self.info_label = ctk.CTkLabel(
            inner, text="", font=FONT_SMALL, text_color=MUTED, anchor="w", justify="left"
        )
        self.info_label.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))

    def _build_mode_card(self):
        card = self._card(row=1, column=0)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=26, pady=22)

        section_title(inner, "⚙️", "Compression method").pack(fill="x", pady=(0, 14))

        self.mode_switch = ctk.CTkSegmentedButton(
            inner, values=["Reduce by percentage", "Keep quality"],
            command=self._on_mode_change, selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
        )
        self.mode_switch.set("Reduce by percentage")
        self.mode_switch.pack(fill="x", pady=(0, 18))

        self.percent_frame = ctk.CTkFrame(inner, fg_color="transparent")
        self.quality_frame = ctk.CTkFrame(inner, fg_color="transparent")
        self._build_percent_frame()
        self._build_quality_frame()
        self.percent_frame.pack(fill="x")

    def _build_percent_frame(self):
        ctk.CTkLabel(
            self.percent_frame, text="How much smaller should the video be?",
            font=FONT_BODY, anchor="w",
        ).pack(fill="x")

        row = ctk.CTkFrame(self.percent_frame, fg_color="transparent")
        row.pack(fill="x", pady=(8, 0))
        row.grid_columnconfigure(0, weight=1)

        self.percent_slider = ctk.CTkSlider(
            row, from_=10, to=90, number_of_steps=80,
            command=self._on_percent_change, progress_color=ACCENT, button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
        )
        self.percent_slider.set(50)
        self.percent_slider.grid(row=0, column=0, sticky="ew", padx=(0, 14))

        self.percent_value_label = ctk.CTkLabel(
            row, text="50%", font=("Segoe UI", 15, "bold"), width=54, text_color=ACCENT
        )
        self.percent_value_label.grid(row=0, column=1)

    def _build_quality_frame(self):
        ctk.CTkLabel(
            self.quality_frame,
            text="A more efficient codec (H.265) with a lower CRF is used, so visual "
                 "quality stays close to the original while the file naturally shrinks.",
            font=FONT_SMALL, text_color=MUTED, anchor="w", justify="left", wraplength=560,
        ).pack(fill="x", pady=(0, 14))

        codec_row = ctk.CTkFrame(self.quality_frame, fg_color="transparent")
        codec_row.pack(fill="x", pady=(0, 14))
        codec_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(codec_row, text="Video codec:", font=FONT_BODY).grid(row=0, column=0, padx=(0, 10))
        self.codec_menu = ctk.CTkOptionMenu(
            codec_row, values=["H.265 (smaller files)", "H.264 (wider compatibility)"],
            fg_color=ACCENT, button_color=ACCENT_HOVER, button_hover_color=ACCENT,
        )
        self.codec_menu.grid(row=0, column=1, sticky="ew")

        quality_row = ctk.CTkFrame(self.quality_frame, fg_color="transparent")
        quality_row.pack(fill="x")
        quality_row.grid_columnconfigure(0, weight=1)

        self.quality_slider = ctk.CTkSlider(
            quality_row, from_=0, to=4, number_of_steps=4,
            command=self._on_quality_change, progress_color=ACCENT, button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
        )
        self.quality_slider.set(2)
        self.quality_slider.grid(row=0, column=0, sticky="ew", padx=(0, 14))

        self.quality_value_label = ctk.CTkLabel(
            quality_row, text="Good", font=("Segoe UI", 15, "bold"), width=70, text_color=ACCENT
        )
        self.quality_value_label.grid(row=0, column=1)

        ctk.CTkLabel(
            self.quality_frame, text="Smaller file  ⟵ ⟶  Higher quality",
            font=FONT_SMALL, text_color=MUTED,
        ).pack(pady=(6, 0))

    def _build_output_card(self):
        card = self._card(row=2, column=0)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=26, pady=22)
        inner.grid_columnconfigure(0, weight=1)

        section_title(inner, "💾", "Output").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))

        self.output_label = ctk.CTkLabel(
            inner, text="Will be saved next to the source file", font=FONT_BODY,
            text_color=MUTED, anchor="w",
        )
        self.output_label.grid(row=1, column=0, sticky="ew", padx=(0, 12))

        ctk.CTkButton(
            inner, text="Choose location...", width=170, height=38, corner_radius=12,
            fg_color="transparent", border_width=1, border_color=BORDER,
            text_color=("black", "white"), hover_color=ACCENT_SOFT,
            command=self.pick_output,
        ).grid(row=1, column=1)

    def _build_action_card(self):
        card = self._card(row=3, column=0)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=26, pady=22)
        inner.grid_columnconfigure(0, weight=1)

        section_title(inner, "🚀", "Run").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 16))

        self.progress_bar = ctk.CTkProgressBar(inner, height=18, corner_radius=9, progress_color=ACCENT)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=(0, 14))

        self.start_btn = ctk.CTkButton(
            inner, text="Start compressing", width=190, height=46, corner_radius=14,
            font=("Segoe UI", 15, "bold"), fg_color=SUCCESS, hover_color=SUCCESS_HOVER,
            command=self.start_compression,
        )
        self.start_btn.grid(row=1, column=1)

        self.progress_text = ctk.CTkLabel(inner, text="", font=FONT_SMALL, text_color=MUTED, anchor="w")
        self.progress_text.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 12))

        self.log_box = ctk.CTkTextbox(
            inner, height=130, corner_radius=12, font=("Consolas", 11),
            fg_color=("#f4f5fa", "#12121a"), border_width=1, border_color=BORDER,
        )
        self.log_box.grid(row=3, column=0, columnspan=2, sticky="nsew")
        self.log_box.configure(state="disabled")

    # ---------------- events ----------------

    def _toggle_theme(self, value):
        ctk.set_appearance_mode("light" if value == "Light" else "dark")

    def _on_mode_change(self, value):
        if value == "Reduce by percentage":
            self.quality_frame.pack_forget()
            self.percent_frame.pack(fill="x")
        else:
            self.percent_frame.pack_forget()
            self.quality_frame.pack(fill="x")

    def _on_percent_change(self, value):
        self.percent_value_label.configure(text=f"{int(value)}%")

    def _on_quality_change(self, value):
        labels = ["Very low (tiny file)", "Low", "Medium", "Good", "Excellent (near-original)"]
        self.quality_value_label.configure(text=labels[int(value)])

    def pick_file(self):
        path = filedialog.askopenfilename(
            title="Select a video",
            filetypes=[("Video files", "*.mp4 *.mkv *.mov *.avi *.webm *.flv *.wmv"), ("All files", "*.*")],
        )
        if not path:
            return
        self.video_path = path
        self.file_label.configure(text=Path(path).name, text_color=("black", "white"))
        self._log(f"Reading file info: {path}")
        threading.Thread(target=self._probe_worker, args=(path,), daemon=True).start()

    def _probe_worker(self, path):
        try:
            info = compressor.get_video_info(self.ffprobe_path, path)
            self.after(0, lambda: self._on_probe_done(info))
        except Exception as exc:
            self.after(0, lambda: self._log(f"Error reading video: {exc}"))

    def _on_probe_done(self, info):
        self.video_info = info
        size_txt = compressor.format_size(info["size_bytes"])
        dur_txt = compressor.format_duration(info["duration"])
        res_txt = f'{info["width"]}x{info["height"]}' if info["width"] else "unknown"
        self.info_label.configure(
            text=f'Size: {size_txt}   •   Duration: {dur_txt}   •   Resolution: {res_txt}   •   Codec: {info["video_codec"]}'
        )
        self._log("Video info loaded successfully.")

    def pick_output(self):
        if not self.video_path:
            messagebox.showinfo(APP_TITLE, "Please select a video first.")
            return
        path = filedialog.asksaveasfilename(
            title="Save output as",
            defaultextension=".mp4",
            initialfile=Path(self.video_path).stem + "_compressed.mp4",
            filetypes=[("MP4", "*.mp4")],
        )
        if path:
            self.custom_output_path = path
            self.output_label.configure(text=path, text_color=("black", "white"))

    def _log(self, text):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    # ---------------- compression ----------------

    def start_compression(self):
        if self.is_running:
            return
        if not self.video_path or not self.video_info:
            messagebox.showinfo(APP_TITLE, "Please select a valid video first.")
            return

        output_path = self.custom_output_path or str(
            Path(self.video_path).with_name(Path(self.video_path).stem + "_compressed.mp4")
        )

        mode = self.mode_switch.get()
        if mode == "Reduce by percentage":
            percent = self.percent_slider.get()
            cmd = compressor.build_percent_mode_cmd(
                self.ffmpeg_path, self.video_path, output_path, self.video_info, percent
            )
        else:
            codec = "libx265" if "H.265" in self.codec_menu.get() else "libx264"
            # Higher quality level -> lower CRF (better quality, bigger file)
            crf_table_265 = [34, 30, 28, 25, 21]
            crf_table_264 = [30, 27, 23, 20, 17]
            level = int(self.quality_slider.get())
            crf = crf_table_265[level] if codec == "libx265" else crf_table_264[level]
            cmd = compressor.build_quality_mode_cmd(self.ffmpeg_path, self.video_path, output_path, crf, codec)

        self.is_running = True
        self.start_btn.configure(state="disabled", text="Working...")
        self.progress_bar.set(0)
        self._log("-" * 44)
        self._log("Starting compression...")

        threading.Thread(target=self._compress_worker, args=(cmd, output_path), daemon=True).start()

    def _compress_worker(self, cmd, output_path):
        try:
            duration = self.video_info["duration"]

            def on_progress(frac):
                self.after(0, lambda: self._update_progress(frac))

            def on_log(line):
                self.after(0, lambda: self._log(line))

            compressor.run_ffmpeg_with_progress(cmd, duration, on_progress, on_log)
            self.after(0, lambda: self._on_compress_done(output_path))
        except Exception as exc:
            self.after(0, lambda: self._on_compress_failed(str(exc)))

    def _update_progress(self, frac):
        self.progress_bar.set(frac)
        self.progress_text.configure(text=f"{int(frac * 100)}% done", text_color=MUTED)

    def _on_compress_done(self, output_path):
        self.is_running = False
        self.start_btn.configure(state="normal", text="Start compressing")
        try:
            new_size = os.path.getsize(output_path)
            old_size = self.video_info["size_bytes"]
            saved_pct = (1 - new_size / old_size) * 100 if old_size else 0
            self._log(
                f"Done! New size: {compressor.format_size(new_size)}"
                f" ({saved_pct:.1f}% smaller than {compressor.format_size(old_size)})"
            )
        except Exception:
            self._log("Compression finished.")

        self.progress_text.configure(text="Done", text_color=SUCCESS)
        if messagebox.askyesno(APP_TITLE, "Compression finished successfully.\nOpen the output folder?"):
            open_in_file_manager(str(Path(output_path).parent))

    def _on_compress_failed(self, msg):
        self.is_running = False
        self.start_btn.configure(state="normal", text="Start compressing")
        self.progress_text.configure(text="Failed", text_color=DANGER)
        self._log(f"Error: {msg}")
        messagebox.showerror(APP_TITLE, f"Compression failed:\n{msg}")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("820x760")
        self.minsize(700, 560)
        self.configure(fg_color=WINDOW_BG)

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)

        self.setup_frame = SetupFrame(self.container, on_ready=self.show_main)
        self.setup_frame.pack(fill="both", expand=True)
        self.main_frame = None

    def show_main(self):
        self.setup_frame.pack_forget()
        self.setup_frame.destroy()
        self.main_frame = MainFrame(self.container)
        self.main_frame.pack(fill="both", expand=True)


if __name__ == "__main__":
    app = App()
    app.mainloop()