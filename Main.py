import tkinter as tk
from tkinter import ttk, Canvas, scrolledtext, filedialog, Menu
from PIL import Image, ImageTk
import os
import random
import re
import time
import uuid

class Sprite:
    def __init__(self, engine, name, x=0, y=0):
        self.engine = engine
        self.id = str(uuid.uuid4())  # Unique identifier
        self.name = name
        self.x = x
        self.y = y
        self.texture = None
        self.color = "white"
        self.width = 50
        self.height = 50
        self.draggable = True
        self.is_dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.canvas_id = None
        self.script = None
        
    def load_texture(self, path):
        try:
            image = Image.open(path)
            image = image.resize((self.width, self.height))
            self.texture = ImageTk.PhotoImage(image)
            return True
        except Exception as e:
            print(f"Error loading texture: {e}")
            return False
            
    def draw(self, canvas):
        if self.texture:
            if self.canvas_id:
                canvas.delete(self.canvas_id)
            self.canvas_id = canvas.create_image(
                self.x, self.y,
                image=self.texture,
                anchor=tk.NW,
                tags=("sprite", self.id)
            )
        else:
            if self.canvas_id:
                canvas.delete(self.canvas_id)
            self.canvas_id = canvas.create_rectangle(
                self.x, self.y,
                self.x + self.width, self.y + self.height,
                fill=self.color,
                outline="white",
                tags=("sprite", self.id)
            )
            
    def contains_point(self, x, y):
        return (self.x <= x <= self.x + self.width and
                self.y <= y <= self.y + self.height)
                
    def start_drag(self, x, y):
        if self.draggable:
            self.is_dragging = True
            self.drag_offset_x = x - self.x
            self.drag_offset_y = y - self.y
            
    def update_drag(self, x, y):
        if self.is_dragging:
            self.x = x - self.drag_offset_x
            self.y = y - self.drag_offset_y
            
    def end_drag(self):
        self.is_dragging = False
        
    def duplicate(self):
        new_sprite = Sprite(self.engine, f"{self.name}_copy", self.x + 20, self.y + 20)
        new_sprite.color = self.color
        new_sprite.width = self.width
        new_sprite.height = self.height
        new_sprite.draggable = self.draggable
        if self.texture:
            new_sprite.texture = self.texture  # Note: This shares the image reference
        return new_sprite
        
    def add_script(self, script_content):
        self.script = script_content

class FlamingEngine:
    def __init__(self, root):
        self.root = root
        self.sprites = {}  # key: sprite.id, value: sprite object
        self.selected_sprite = None
        self.is_running = False
        self.last_frame_time = 0
        self.fps = 60
        self.context_menu = None
        self.drag_source = None
        
        # Main layout
        self.paned_window = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Left panel (Scene tree and inspector)
        self.left_panel = ttk.Frame(self.paned_window, width=200)
        self.paned_window.add(self.left_panel)
        
        # Scene tree
        self.scene_tree = ttk.Treeview(self.left_panel)
        self.scene_tree.pack(fill=tk.BOTH, expand=True)
        self.scene_tree.bind("<<TreeviewSelect>>", self.on_sprite_select)
        
        # Setup drag and drop for scene tree
        self.scene_tree.bind("<ButtonPress-1>", self.start_tree_drag)
        self.scene_tree.bind("<B1-Motion>", self.on_tree_drag)
        self.scene_tree.bind("<ButtonRelease-1>", self.end_tree_drag)
        
        # Inspector
        self.inspector_frame = ttk.LabelFrame(self.left_panel, text="Inspector")
        self.inspector_frame.pack(fill=tk.BOTH, expand=True)
        
        # Game canvas
        self.canvas_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.canvas_frame)
        
        self.canvas = Canvas(self.canvas_frame, bg="black", width=800, height=600)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Canvas event bindings
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Button-3>", self.on_right_click)  # Right-click
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        
        # Toolbar
        self.toolbar = ttk.Frame(root)
        self.toolbar.pack(fill=tk.X)
        
        self.load_texture_btn = ttk.Button(
            self.toolbar, 
            text="Load Texture", 
            command=self.load_texture
        )
        self.load_texture_btn.pack(side=tk.LEFT)
        
        # Create test object
        self.test_sprite = self.create_sprite("TestObject", 100, 100)
        self.test_sprite.color = "#3498db"  # Nice blue color
        
        # Context menu
        self.create_context_menu()
        
    def create_context_menu(self):
        self.context_menu = Menu(self.root, tearoff=0)
        self.context_menu.add_command(
            label="Duplicate", 
            command=lambda: self.duplicate_sprite(self.selected_sprite)
        )
        self.context_menu.add_command(
            label="Remove", 
            command=lambda: self.remove_sprite(self.selected_sprite)
        )
        self.context_menu.add_command(
            label="Add Script", 
            command=lambda: self.add_script_to_sprite(self.selected_sprite)
        )
        
    def create_sprite(self, name, x=0, y=0):
        sprite = Sprite(self, name, x, y)
        self.sprites[sprite.id] = sprite
        self.update_scene_tree()
        return sprite
        
    def load_texture(self):
        path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg")]
        )
        if path and self.selected_sprite:
            if self.selected_sprite.load_texture(path):
                self.update_inspector()
                
    def update_scene_tree(self):
        self.scene_tree.delete(*self.scene_tree.get_children())
        for sprite in self.sprites.values():
            self.scene_tree.insert("", "end", iid=sprite.id, text=sprite.name, values=(sprite.name))
            
    def update_inspector(self):
        # Clear inspector
        for widget in self.inspector_frame.winfo_children():
            widget.destroy()
            
        if not self.selected_sprite:
            return
            
        sprite = self.selected_sprite
        
        # Name
        ttk.Label(self.inspector_frame, text="Name:").grid(row=0, column=0, sticky="w")
        name_entry = ttk.Entry(self.inspector_frame)
        name_entry.insert(0, sprite.name)
        name_entry.grid(row=0, column=1, sticky="ew")
        name_entry.bind("<FocusOut>", lambda e: self.update_sprite_property("name", name_entry.get()))
        
        # Position
        ttk.Label(self.inspector_frame, text="Position:").grid(row=1, column=0, sticky="w")
        
        ttk.Label(self.inspector_frame, text="X:").grid(row=2, column=0, sticky="w")
        x_entry = ttk.Entry(self.inspector_frame)
        x_entry.insert(0, str(sprite.x))
        x_entry.grid(row=2, column=1, sticky="ew")
        x_entry.bind("<FocusOut>", lambda e: self.update_sprite_property("x", int(x_entry.get())))
        
        ttk.Label(self.inspector_frame, text="Y:").grid(row=3, column=0, sticky="w")
        y_entry = ttk.Entry(self.inspector_frame)
        y_entry.insert(0, str(sprite.y))
        y_entry.grid(row=3, column=1, sticky="ew")
        y_entry.bind("<FocusOut>", lambda e: self.update_sprite_property("y", int(y_entry.get())))
        
        # Script button
        script_btn = ttk.Button(
            self.inspector_frame,
            text="Edit Script" if sprite.script else "Add Script",
            command=lambda: self.add_script_to_sprite(sprite)
        )
        script_btn.grid(row=7, column=0, columnspan=2, sticky="ew")
        
    def update_sprite_property(self, prop, value):
        if self.selected_sprite:
            setattr(self.selected_sprite, prop, value)
            self.update_scene_tree()
            
    def on_sprite_select(self, event):
        item = self.scene_tree.selection()[0]
        sprite_id = item
        self.selected_sprite = self.sprites.get(sprite_id)
        self.update_inspector()
        
    def on_canvas_click(self, event):
        clicked_sprite = None
        # Find all items at the click position
        items = self.canvas.find_overlapping(event.x, event.y, event.x+1, event.y+1)
        
        # Check if any of them are sprites
        for item in items:
            tags = self.canvas.gettags(item)
            if "sprite" in tags:
                sprite_id = tags[1]  # Second tag is the sprite ID
                clicked_sprite = self.sprites.get(sprite_id)
                break
                
        if clicked_sprite:
            self.selected_sprite = clicked_sprite
            clicked_sprite.start_drag(event.x, event.y)
            self.update_inspector()
            
            # Select in scene tree
            self.scene_tree.selection_set(clicked_sprite.id)
            
    def on_right_click(self, event):
        # Find sprite at right-click position
        clicked_sprite = None
        items = self.canvas.find_overlapping(event.x, event.y, event.x+1, event.y+1)
        
        for item in items:
            tags = self.canvas.gettags(item)
            if "sprite" in tags:
                sprite_id = tags[1]
                clicked_sprite = self.sprites.get(sprite_id)
                break
                
        if clicked_sprite:
            self.selected_sprite = clicked_sprite
            self.scene_tree.selection_set(clicked_sprite.id)
            self.context_menu.post(event.x_root, event.y_root)
            
    def on_canvas_drag(self, event):
        if self.selected_sprite:
            self.selected_sprite.update_drag(event.x, event.y)
            self.render()  # Immediate feedback
            
    def on_canvas_release(self, event):
        if self.selected_sprite:
            self.selected_sprite.end_drag()
            
    def start_tree_drag(self, event):
        item = self.scene_tree.identify_row(event.y)
        if item:
            self.drag_source = item
            self.scene_tree.selection_set(item)
            
    def on_tree_drag(self, event):
        if self.drag_source:
            # Visual feedback could be added here
            pass
            
    def end_tree_drag(self, event):
        if self.drag_source:
            # Check if we're over the canvas
            if (event.x > self.left_panel.winfo_width() and 
                event.y < self.canvas.winfo_height()):
                
                # Get original sprite
                original_sprite = self.sprites.get(self.drag_source)
                if original_sprite:
                    # Create new sprite at mouse position (adjusted for panel width)
                    canvas_x = event.x - self.left_panel.winfo_width()
                    canvas_y = event.y
                    new_sprite = original_sprite.duplicate()
                    new_sprite.x = canvas_x
                    new_sprite.y = canvas_y
                    self.sprites[new_sprite.id] = new_sprite
                    self.update_scene_tree()
                    
            self.drag_source = None
            
    def duplicate_sprite(self, sprite):
        if sprite:
            new_sprite = sprite.duplicate()
            self.sprites[new_sprite.id] = new_sprite
            self.update_scene_tree()
            
    def remove_sprite(self, sprite):
        if sprite:
            if sprite.id in self.sprites:
                del self.sprites[sprite.id]
                self.selected_sprite = None
                self.update_scene_tree()
                self.update_inspector()
                
    def add_script_to_sprite(self, sprite):
        if sprite:
            # Create a popup window for script editing
            script_window = tk.Toplevel(self.root)
            script_window.title(f"Script Editor - {sprite.name}")
            script_window.geometry("600x400")
            
            # Script editor
            editor = scrolledtext.ScrolledText(script_window, font=('Consolas', 12))
            editor.pack(fill=tk.BOTH, expand=True)
            
            if sprite.script:
                editor.insert(tk.END, sprite.script)
                
            # Save button
            def save_script():
                sprite.script = editor.get("1.0", tk.END)
                script_window.destroy()
                self.update_inspector()
                
            save_btn = ttk.Button(script_window, text="Save", command=save_script)
            save_btn.pack(side=tk.BOTTOM, pady=5)
            
    def start(self):
        self.is_running = True
        self.game_loop()
        
    def stop(self):
        self.is_running = False
        
    def game_loop(self):
        if not self.is_running:
            return
            
        current_time = time.time()
        delta_time = current_time - self.last_frame_time if self.last_frame_time else 0
        self.last_frame_time = current_time
        
        self.update(delta_time)
        self.render()
        
        self.root.after(int(1000/self.fps), self.game_loop)
        
    def update(self, delta_time):
        # Execute sprite scripts
        for sprite in self.sprites.values():
            if sprite.script:
                # In a real implementation, we'd interpret the script here
                pass
                
    def render(self):
        self.canvas.delete("all")
        for sprite in self.sprites.values():
            sprite.draw(self.canvas)

class FlamingEngineIDE:
    def __init__(self, root):
        self.root = root
        self.root.title("Flaming Engine - DEMO")
        self.root.geometry("1200x800")
        
        # Create engine
        self.engine = FlamingEngine(root)
        
        # Start the engine
        self.engine.start()

if __name__ == "__main__":
    root = tk.Tk()
    ide = FlamingEngineIDE(root)
    root.mainloop()
