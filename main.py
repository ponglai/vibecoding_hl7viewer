import tkinter as tk
from viewer import HL7ViewerApp

if __name__ == "__main__":
    root = tk.Tk()
    app = HL7ViewerApp(root)
    root.mainloop()
