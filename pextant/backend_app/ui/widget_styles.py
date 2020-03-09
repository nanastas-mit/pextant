import tkinter.ttk as ttk


class UIStyleManager:

    @staticmethod
    def initialize_styles():

        s = ttk.Style()

        # Frame
        s.configure('Banner.TFrame', borderwidth=2, relief='groove')
        s.configure('BannerCell.TFrame', borderwidth=2, relief='groove')

