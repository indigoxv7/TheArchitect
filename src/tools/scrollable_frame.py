import tkinter as tk
from tkinter import ttk


class ScrollableEditorHost(ttk.Frame):
    def __init__(self, parent, frame_cls, *args, **kwargs):
        super().__init__(parent)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        self._canvas.grid(row=0, column=0, sticky="nsew")

        self._scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._canvas.yview)
        self._scrollbar.grid(row=0, column=1, sticky="ns")
        self._canvas.configure(yscrollcommand=self._on_canvas_scroll)

        self._content_parent = ttk.Frame(self._canvas)
        self._window_id = self._canvas.create_window((0, 0), window=self._content_parent, anchor="nw")

        self.content = frame_cls(self._content_parent, *args, **kwargs)
        self.content.pack(fill=tk.BOTH, expand=True)

        self._scrollbar_visible = True
        self._content_parent.bind("<Configure>", self._on_content_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self.after_idle(self._refresh_scroll_state)

    def __getattr__(self, name):
        return getattr(self.content, name)

    def _on_canvas_scroll(self, first, last):
        self._scrollbar.set(first, last)
        self._refresh_scroll_state()

    def _on_content_configure(self, _event=None):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        self._refresh_scroll_state()

    def _on_canvas_configure(self, event):
        self._canvas.itemconfigure(self._window_id, width=event.width)
        self._refresh_scroll_state()

    def _refresh_scroll_state(self):
        self.update_idletasks()
        needs_scrollbar = self.content.winfo_reqheight() > self._canvas.winfo_height()
        if needs_scrollbar and not self._scrollbar_visible:
            self._scrollbar.grid()
            self._scrollbar_visible = True
        elif not needs_scrollbar and self._scrollbar_visible:
            self._scrollbar.grid_remove()
            self._scrollbar_visible = False

    def scroll_to_top(self):
        self._canvas.yview_moveto(0.0)
        self._refresh_scroll_state()
