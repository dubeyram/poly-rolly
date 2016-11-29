#! /usr/bin/python3

from datetime import datetime as dt
from json     import dumps , load
from os.path  import isfile, split
from random   import SystemRandom
from time     import sleep
from tkinter  import (
           BooleanVar,
           Button    ,
           Entry     ,
           Frame     ,
           IntVar    ,
           Label     ,
           LabelFrame,
           Menu      ,
           Menubutton,
           PhotoImage,
           Spinbox   ,
           StringVar ,
           Tk        )
from tkinter.messagebox import askyesno
from tkinter.filedialog import askopenfilename, asksaveasfilename
from urllib .request    import urlopen


_title        = 'Poly Rolly v2.1  -  mznlab.net'
roller_groups = []
CRIT          = 1000
FAIL          = .001

def maintain_group_indices():
    for group in roller_groups:
        group.index = roller_groups.index(group)
        group.grid(row=group.index)

def maintain_tabstops():
    for group in roller_groups:
        for r in group.rollers:
            r.lift()
        group.lift()
        group.control_frame.lift()

class MainFrame(Frame):
    def set_saved_title(self, fpath):
        fname = split(fpath)[-1].replace('.json', '')
        self.master.title('{}  -  {}'.format(fname, _title))

    def set_unsaved_title(self, *args):
        if len(roller_groups) < 1:
            return
        if self.autosave.get():
            self.save_config(self.fpath)
            return
        title = self.master.title()
        if title == _title:
            title = '{}  -  {}'.format('Unsaved', title)
        if '*' not in title:
            title = '*' + title

        self.master.title(title)

    def __init__(self, master):
        Frame.__init__(self, master)

        self.master = master

        self.use_random_org = BooleanVar()
        self.allow_odd      = IntVar()
        self.always_on_top  = BooleanVar()
        self.autosave       = BooleanVar()

        self.use_random_org.trace('w', self.set_unsaved_title)
        self.allow_odd     .trace('w', self.set_unsaved_title)
        self.always_on_top .trace('w', self.set_unsaved_title)

        self.set_defaults()

        self.menubar = Menu(master)

        self.filemenu = Menu(self.menubar, tearoff=0, postcommand=maintain_group_indices)
        self.filemenu.add_command(label='New'       , underline=0, command=        self.reset_default_group          , accelerator='Ctrl+N'      )
        self.filemenu.add_command(label='Load'      , underline=3, command=        self.load_config                  , accelerator='Ctrl+D'      )
        self.filemenu.add_command(label='Save'      , underline=1, command=lambda: self.save_config(fpath=self.fpath), accelerator='Ctrl+S'      )
        self.filemenu.add_command(label='Save as...', underline=4, command=        self.save_config                  , accelerator='Ctrl+Shift+S')

        self.editmenu = Menu(self.menubar, tearoff=0)
        self.editmenu.add_checkbutton(label='Use random.org'    , underline=0 , variable=self.use_random_org                                                 )
        self.editmenu.add_checkbutton(label='Allow odd dice'    , underline=6 , variable=self.allow_odd      , command=self.toggle_odd, onvalue=1, offvalue=2)
        self.editmenu.add_separator() #      ------------------
        self.editmenu.add_checkbutton(label='Always on top'     , underline=10, variable=self.always_on_top  , command=self.pin                              )
        self.editmenu.add_checkbutton(label='Autosave'          , underline=4 , variable=self.autosave       , command=self.toggle_autosave                  )
        self.editmenu.add_separator() #      ------------------
        self.editmenu.add_command    (label='Repeat last action', underline=0 , accelerator='Ctrl+R'                                                         )

        self.menubar.add_cascade(label='File', underline=0, menu=self.filemenu)
        self.menubar.add_cascade(label='Edit', underline=0, menu=self.editmenu)

        self.menubar.config(relief='flat')

        master.config(menu=self.menubar)

        self.reset_default_group()

        self.bind_all('<Control-n>'      , lambda e: self.reset_default_group()        )
        self.bind_all('<Control-d>'      , lambda e: self.load_config()                )
        self.bind_all('<Control-s>'      , lambda e: self.save_config(fpath=self.fpath))
        self.bind_all('<Control-Shift-S>', lambda e: self.save_config()                )

    def ask_proceed(self):
        if '*' in self.master.title():
            if not askyesno('Unsaved changes!', 'There are unsaved changes!\r\nWould you like to proceed anyway?'):
                return False
        return True

    def pin(self):
        self.master.wm_attributes('-topmost', self.always_on_top.get())

    def toggle_odd(self):
        for group in roller_groups:
            for roller in group.rollers:
                roller.die_faces_spin.interval = self.allow_odd.get()
                num = roller.die_faces.get()
                if num % 2 != 0:
                    roller.die_faces.set(num - 1)

    def toggle_autosave(self):
        if self.autosave.get():
            self.save_config(self.fpath)
        else:
            self.set_unsaved_title()

    def set_defaults(self):
        self.master.title(_title)
        self.fpath = ''
        self.use_random_org.set(False)
        self.allow_odd     .set(2)
        self.always_on_top .set(False)
        self.autosave      .set(False)

    def reset_default_group(self):
        if self.ask_proceed():
            self.autosave.set(False)
            self.clear_groups()
            self.set_defaults()
            self.create_group(0, 1)

    @staticmethod
    def clear_groups():
        temp_groups = list(roller_groups)
        for group in temp_groups:
            group.remove_group(override=True)

    def create_group(self, index, rollers):
        default_group = RollerGroup(self, index)
        for i in range(rollers):
            default_group.rollers.append(Roller(default_group, i))
        roller_groups.append(default_group)

    def load_config(self):
        autosave = False
        self.autosave.set(autosave)
        if not self.ask_proceed():
            return

        fpath = askopenfilename(filetypes=[('JSON', '*.json'), ('All', '*.*')], defaultextension='.json')
        if not fpath or not isfile(fpath):
            return
        self.fpath = fpath

        self.clear_groups()

        with open(fpath, 'r') as f:
            group_dict = load(f)

        try:
            settings_dict = group_dict.pop('settings')
            autosave      = (settings_dict['autosave'])
            self.use_random_org.set(settings_dict['use_random_org'])
            self.allow_odd     .set(settings_dict['allow_odd'     ])
            self.always_on_top .set(settings_dict['always_on_top' ])
        except KeyError:
            pass

        g = 0
        for group_name, group_settings in group_dict.items():
            self.create_group(g, len(group_settings['rollers']))

            group = roller_groups[g]
            group.name.set(group_name)
            group.index = group_settings['index']

            r = 0
            h = 0
            for roller_name, roller_settings in group_settings['rollers'].items():
                roller = group.rollers[r]
                roller.name.set(roller_name)
                for attr, value in roller_settings.items():
                    try:
                        getattr(roller, attr).set(value)
                    except AttributeError:
                        setattr(roller, attr, value)
                roller.reset(loading=True)
                h = len(roller.history) - 1
                r += 1

            group.navigate_history(desired_index=h)
            g += 1

        roller_groups.sort(key=lambda x: x.index)

        maintain_group_indices()
        for group in roller_groups:
            group.rollers.sort(key=lambda x: x.index)
            group.maintain_roller_indices()
            for roller in group.rollers:
                roller.apply_modifiers()

        maintain_tabstops()

        self.pin()
        self.autosave.set(autosave)
        self.set_saved_title(fpath)

    def save_config(self, fpath=''):
        if not fpath:
            fpath = asksaveasfilename(filetypes=[('JSON', '*.json'), ('All', '*.*')], defaultextension='.json')
        if not fpath:
            if '*' in self.master.title():
                self.autosave.set(False)
            return
        self.fpath = fpath

        d1 = {}
        d1['settings'] = {'use_random_org': self.use_random_org.get(),
                          'allow_odd'     : self.allow_odd     .get(),
                          'always_on_top' : self.always_on_top .get(),
                          'autosave'      : self.autosave      .get()}
        for group in roller_groups:
            group.maintain_roller_indices()
            d2 = {}
            d2['index'] = group.index
            d2['rollers'] = {}
            for roller in group.rollers:
                name = roller.name.get()
                while name in d2['rollers']:
                    name += '!'
                d2['rollers'][name] = {'index'    : roller.index          ,
                                       'history'  : roller.history        ,
                                       'dice_qty' : roller.dice_qty .get(),
                                       'die_faces': roller.die_faces.get(),
                                       'modifier' : roller.modifier .get(),
                                       'finalmod' : roller.finalmod .get()}
            name = group.name.get()
            if name in d1:
                name += '!'
            d1[name] = d2

        with open(fpath, 'w') as f:
            f.write(dumps(d1, indent=2, separators=(',', ': ')))

        self.set_saved_title(fpath)


class RollerGroup(LabelFrame):
    def __init__(self, mainframe, index):
        LabelFrame.__init__(self, mainframe)

        self.mainframe     = mainframe
        self.index         = index
        self.hist_index    = 0
        self.collapsed     = False
        self.rollers       = []
        self.control_frame = Frame(None)
        default_font       = ('Verdana', 10)

        self.name = StringVar()
        self.name.trace('w', self.mainframe.set_unsaved_title)

        self.expand_img   = PhotoImage(data=b'R0lGODlhEAAQAIABAAAAAP///yH5BAEKAAEALAAAAAAQABAAAAIlhI+pq+EPHYo0TGjifRkfDYAdI33WUnZc6KmlyK5wNdMrg+dJAQA7')
        self.collapse_img = PhotoImage(data=b'R0lGODlhEAAQAIABAAAAAP///yH5BAEKAAEALAAAAAAQABAAAAIfhI+pq+EPHYo0zAovlme/y3CGmJCeeWqbirEVA8dLAQA7'        )

        self.collapse_btn  = Button    (self.control_frame, bd=0, image=self.collapse_img, command=self.show_hide                                       )
        self.menu_btn      = Menubutton(self.control_frame, bd=1, relief='solid', font=('Courier',  8), text='\u25e2', takefocus=1, highlightthickness=1)
        self.name_entry    = Entry     (self.control_frame, bd=1, relief='solid', font=('Verdana', 12), width=16     , textvariable=self.name           )

        self.history_frame = LabelFrame(self.control_frame, bd=1, text='History', relief='solid', font=default_font, labelanchor='w')
        self.roll_frame    = LabelFrame(self.control_frame, bd=1, text='Roll'   , relief='solid', font=default_font, labelanchor='w')

        self.roll_img    = PhotoImage(data=b'R0lGODlhDgARAIABAAAAAP///yH5BAEKAAEALAAAAAAOABEAAAIkjB+Ai6C83GOy0iqjM7ltPoFhKEKeKZJadynfVa6HlbAp3ZIFADs=')
        self.left_arrow  = PhotoImage(data=b'R0lGODlhBwANAIABAAAAAP///yH5BAEKAAEALAAAAAAHAA0AAAITjA9nkMj+Apty2lvt0jt2VYFSAQA7')
        self.right_arrow = PhotoImage(data=b'R0lGODlhBwANAIABAAAAAP///yH5BAEKAAEALAAAAAAHAA0AAAITRI5gGLrnXlzT1NsidEkx/zFHAQA7')

        self.roll_btn      = Button(self.roll_frame   , bd=0, image=self.roll_img   , height=24, command=self.roll_group                                                                        )
        self.hist_prev_btn = Button(self.history_frame, bd=0, image=self.left_arrow , height=24, width=16, repeatdelay=250, repeatinterval=100, command=lambda: self.navigate_history(offset=-1))
        self.hist_next_btn = Button(self.history_frame, bd=0, image=self.right_arrow, height=24, width=16, repeatdelay=250, repeatinterval=100, command=lambda: self.navigate_history(offset= 1))

        self.menu_btn.config(menu=self.create_menu())

        self.collapse_btn .grid(row=0, column=0, padx=(4, 0))
        self.menu_btn     .grid(row=0, column=1, padx=(4, 0))
        self.name_entry   .grid(row=0, column=2, padx=(4, 0))
        self.history_frame.grid(row=0, column=3, padx=(6, 0))
        self.hist_prev_btn.grid(row=0, column=0, padx=(6, 0))
        self.hist_next_btn.grid(row=0, column=1, padx=(0, 2))
        self.roll_frame   .grid(row=0, column=4, padx=(6, 4))
        self.roll_btn     .grid(row=0, column=0, padx=(6, 2))

        self.config(relief='solid', labelwidget=self.control_frame)
        self.name.set('Group {}'.format(len(roller_groups) + 1))
        self.grid(row=index, padx=4, pady=4, sticky='w')

    def show_hide(self):
        if self.collapsed:
            for roller in self.rollers:
                roller.grid()
            self.collapse_btn.config(image=self.collapse_img)
            self.collapsed = False
        else:
            for roller in self.rollers:
                roller.grid_remove()
            self.collapse_btn.config(image=self.expand_img)
            width = 28 + self.collapse_btn.winfo_width() + self.menu_btn.winfo_width() + self.name_entry.winfo_width()
            self.config(height=36, width=width)
            self.collapsed = True

    def create_menu(self):
        menu = Menu(self.menu_btn, tearoff=0, postcommand=maintain_group_indices)

        menu.add_command(label='Add'          , underline=0, command=        self.add_group             )
        menu.add_command(label='Clone'        , underline=0, command=lambda: self.add_group (clone=True))
        menu.add_command(label='Up'           , underline=0, command=lambda: self.move_group(offset=-1) )
        menu.add_command(label='Down'         , underline=0, command=lambda: self.move_group(offset= 1) )
        menu.add_separator() #  -------------
        menu.add_command(label='Clear history', underline=6, command=        self.clear_history         )
        menu.add_command(label='Remove'       , underline=0, command=        self.remove_group          )

        return menu

    def add_group(self, clone=False):
        destination_index = self.index + 1

        group = RollerGroup(self.mainframe, destination_index)
        roller_groups.insert(group.index, group)

        for i in range(destination_index, len(roller_groups)):
            roller_groups[i].grid(row=i + 1)

        if clone:
            for roller in self.rollers:
                new_roller = Roller(group, self.rollers.index(roller))
                new_roller.name     .set(roller.name     .get())
                new_roller.dice_qty .set(roller.dice_qty .get())
                new_roller.die_faces.set(roller.die_faces.get())
                new_roller.modifier .set(roller.modifier .get())
                new_roller.finalmod .set(roller.finalmod .get())
                group.rollers.append(new_roller)
            group.name.set(self.name.get())
        else:
            group.rollers.append(Roller(group, 0))
            group.name.set(group.name.get())

        maintain_tabstops()

        self.mainframe.editmenu.entryconfigure(
            self.mainframe.editmenu.index('end'), command=lambda: self.add_group(clone=clone))
        self.mainframe.bind_all('<Control-r>', lambda e: self.add_group(clone=clone))

    def move_group(self, offset=0, destination_index=0):
        if not destination_index:
            destination_index = self.index + offset

        if destination_index >= 0:
            group = roller_groups.pop(self.index)
            roller_groups.insert(destination_index, group)

        maintain_group_indices()
        self.name.set(self.name.get())

        self.mainframe.editmenu.entryconfigure(
            self.mainframe.editmenu.index('end'), command=lambda: self.move_group(offset=offset))
        self.mainframe.bind_all('<Control-r>', lambda e: self.move_group(offset=offset))

    def clear_history(self):
        for roller in self.rollers:
            roller.reset()
            roller.history = []
        self.history_frame.config(text='History')

    def remove_group(self, override=False):
        if len(roller_groups) > 1 or override:
            self.grid_remove()
            roller_groups.remove(self)
            self.name.set('')

    def maintain_roller_indices(self):
        for roller in self.rollers:
            roller.index = self.rollers.index(roller)
            roller.grid(row=roller.index)

    def roll_group(self):
        for roller in self.rollers:
            roller.roll()

        self.navigate_history()

        self.mainframe.editmenu.entryconfigure(
            self.mainframe.editmenu.index('end'), command=lambda: self.roll_group())
        self.mainframe.bind_all('<Control-r>', lambda e: self.roll_group())

    def navigate_history(self, offset=0, desired_index=0):
        hist_len = len(self.rollers[0].history)
        if not hist_len:
            return

        if not desired_index:
            desired_index = self.hist_index + offset

        if desired_index >= -1 and desired_index <= hist_len:
            if desired_index == -1:
                desired_index = 0
            if desired_index == hist_len:
                desired_index = hist_len - 1
            for roller in self.rollers:
                hist_dict      = roller.history[desired_index]
                roller.results = hist_dict['results']
                roller.dice_qty    .set(hist_dict['dice_qty'    ])
                roller.die_faces   .set(hist_dict['die_faces'   ])
                roller.modifier    .set(hist_dict['modifier'    ])
                roller.results_text.set(hist_dict['results_text'])
                roller.finalmod    .set(hist_dict['finalmod'    ])
                self.history_frame.config(text=hist_dict['timestamp'])
            self.hist_index = desired_index

        self.maintain_result_widths()

    def maintain_result_widths(self):
        for roller in self.rollers:
            w = len(roller.results_text.get())
            if w > 80:
                w = 80
            roller.results_entry.config(width=w)


class NumericSpinner(Frame):
    def __init__(self, master, variable, low, high, interval=1, initial=0, callback=None):
        Frame.__init__(self, master)

        self.master   = master
        self.low      = low
        self.high     = high
        self.interval = interval
        self.variable = variable
        self.callback = callback

        if initial > low:
            self.variable.set(initial)
        else:
            self.variable.set(low)

        self.entry     = Entry(self, width=len(str(self.variable.get())), textvariable=self.variable, bd=0, font=('Courier', 14), state='readonly', relief='solid')
        self.btn_frame = Frame(self)

        self.up_arrow = PhotoImage(data=b'R0lGODlhCQAFAIABAAAAAP///yH5BAEKAAEALAAAAAAJAAUAAAILjAOnwIrcDJxvwgIAOw==')
        self.dn_arrow = PhotoImage(data=b'R0lGODlhCQAFAIABAAAAAP///yH5BAEKAAEALAAAAAAJAAUAAAIKhH+BGYoNGWxgFgA7'    )

        self.up_btn = Button(self.btn_frame, width=10, height=8, bd=0, image=self.up_arrow, repeatdelay=500, repeatinterval=100, command=lambda: self.step( 1))
        self.dn_btn = Button(self.btn_frame, width=10, height=8, bd=0, image=self.dn_arrow, repeatdelay=500, repeatinterval=100, command=lambda: self.step(-1))

        self.up_btn.grid(row=0)
        self.dn_btn.grid(row=1)

        self.entry    .grid(column=0, row=0            )
        self.btn_frame.grid(column=1, row=0, padx=(2,0))

    def step(self, m):
        n = self.variable.get()
        n += self.interval * m
        if m:
            if n > self.high:
                self.variable.set(self.high)
            elif n < self.low:
                self.variable.set(self.low)
            else:
                self.variable.set(n)
            if self.callback:
                self.callback()
        self.entry.config(width=len(str(n)))


class Roller(Frame):
    def __init__(self, group, index):
        Frame.__init__(self, group)

        self.group   = group
        self.index   = index
        self.results = [0]
        self.history = []

        self.name         = StringVar()
        self.dice_qty     = IntVar()
        self.die_faces    = IntVar()
        self.modifier     = IntVar()
        self.finalmod     = IntVar()
        self.results_text = StringVar()

        self.name        .trace('w', self.group.mainframe.set_unsaved_title)
        self.dice_qty    .trace('w', self.group.mainframe.set_unsaved_title)
        self.die_faces   .trace('w', self.group.mainframe.set_unsaved_title)
        self.modifier    .trace('w', self.group.mainframe.set_unsaved_title)
        self.finalmod    .trace('w', self.group.mainframe.set_unsaved_title)
        self.results_text.trace('w', self.group.mainframe.set_unsaved_title)

        default_font = ('Courier', 14)

        self.menu_btn   = Menubutton(self, bd=1, relief='solid', font=('Courier',  8), text='\u25e2', takefocus=1, highlightthickness=1)
        self.name_entry = Entry     (self, bd=1, relief='solid', font=('Verdana', 12), width=16     , textvariable=self.name           )

        self.dice_qty_spin  = NumericSpinner(self, self.dice_qty ,   1,  99, callback=self.reset                          , initial=1 )
        self.die_faces_spin = NumericSpinner(self, self.die_faces,   2, 100, interval=self.group.mainframe.allow_odd.get(), initial=10)
        self.modifier_spin  = NumericSpinner(self, self.modifier , -99, 100, callback=self.apply_modifiers                            )
        self.finalmod_spin  = NumericSpinner(self, self.finalmod , -99, 100, callback=self.apply_modifiers                            )
        self.dice_lbl       = Label(self, text=' d'    , font=default_font                                                            )
        self.modifier_lbl   = Label(self, text='\u002b', font=default_font                                                            )
        self.finalmod_lbl   = Label(self, text='\u002b', font=default_font                                                            )

        self.roll_btn      = Button(self, bd=0, image=self.group.roll_img, command=lambda: self.roll(single=True))
        self.results_entry = Entry (self, bd=0, relief='solid', font=default_font, width=0, textvariable=self.results_text, state='readonly', justify='center')

        self.menu_btn.config(menu=self.create_menu())

        self.menu_btn      .grid(row=index, column=0 , padx=(4, 0))
        self.name_entry    .grid(row=index, column=1 , padx=(4, 0))
        self.dice_qty_spin .grid(row=index, column=2 , padx=(4, 0))
        self.dice_lbl      .grid(row=index, column=3 , padx=(0, 0))
        self.die_faces_spin.grid(row=index, column=4 , padx=(0, 0))
        self.modifier_lbl  .grid(row=index, column=5 , padx=(6, 6))
        self.modifier_spin .grid(row=index, column=6 , padx=(0, 0))
        self.roll_btn      .grid(row=index, column=7 , padx=(8, 0))
        self.results_entry .grid(row=index, column=8 , padx=(8, 0))
        self.finalmod_lbl  .grid(row=index, column=9 , padx=(6, 6))
        self.finalmod_spin .grid(row=index, column=10, padx=(0, 4))

        self.name        .set('Roller {}'.format(len(self.group.rollers) + 1))
        self.die_faces   .set(10)
        self.results_text.set('0 = 0')

        self.grid(row=index, sticky='w', pady=4)

    def create_menu(self):
        menu = Menu(self.menu_btn, tearoff=0, postcommand=self.group.maintain_roller_indices)

        menu.add_command(label='Add'   , underline=0, command=        self.add_roller             )
        menu.add_command(label='Clone' , underline=0, command=lambda: self.add_roller (clone=True))
        menu.add_command(label='Up'    , underline=0, command=lambda: self.move_roller(offset=-1) )
        menu.add_command(label='Down'  , underline=0, command=lambda: self.move_roller(offset= 1) )
        menu.add_separator() #  ------
        menu.add_command(label='Remove', underline=0, command=        self.remove_roller          )

        return menu

    def create_hist_record(self):
        record = {
            'dice_qty'    : self.dice_qty    .get() ,
            'die_faces'   : self.die_faces   .get() ,
            'modifier'    : self.modifier    .get() ,
            'results_text': self.results_text.get() ,
            'finalmod'    : self.finalmod    .get() ,
            'timestamp'   : str(dt.now().time())[:8],
            'results'     : self.results            }
        return record

    def add_roller(self, clone=False):
        destination_index = self.index + 1

        roller = Roller(self.group, destination_index)
        self.group.rollers.insert(roller.index, roller)

        for i in range(destination_index, len(self.group.rollers)):
            self.group.rollers[i].grid(row=i + 1)

        if clone:
            roller.name     .set(self.name     .get())
            roller.dice_qty .set(self.dice_qty .get())
            roller.die_faces.set(self.die_faces.get())
            roller.modifier .set(self.modifier .get())
            roller.finalmod .set(self.finalmod .get())
            roller.reset()

        for h in self.history:
            record = roller.create_hist_record()
            record['timestamp'] = h['timestamp']
            roller.history.append(record)

        roller.apply_modifiers()

        for r in self.group.rollers:
            r.lift()

        self.group.mainframe.editmenu.entryconfigure(
            self.group.mainframe.editmenu.index('end'), command=lambda: self.add_roller(clone=clone))
        self.group.mainframe.bind_all('<Control-r>', lambda e: self.add_roller(clone=clone))

    def move_roller(self, offset=0, destination_index=0):
        if not destination_index:
            destination_index = self.index + offset

        if destination_index >= 0:
            roller = self.group.rollers.pop(self.index)
            self.group.rollers.insert(destination_index, roller)

        self.group.maintain_roller_indices()
        self.name.set(self.name.get())

        self.group.mainframe.editmenu.entryconfigure(
            self.group.mainframe.editmenu.index('end'), command=lambda: self.move_roller(offset=offset))
        self.group.mainframe.bind_all('<Control-r>', lambda e: self.move_roller(offset=offset))

    def remove_roller(self):
        if len(self.group.rollers) > 1:
            self.grid_remove()
            self.group.rollers.remove(self)
            self.name.set('')

    def reset(self, loading=False):
        self.results = [0 for i in range(self.dice_qty.get())]
        self.dice_qty_spin .step(0)
        self.die_faces_spin.step(0)
        self.modifier_spin .step(0)
        self.finalmod_spin .step(0)
        if not loading:
            self.apply_modifiers()
            self.group.maintain_result_widths()

    def roll(self, single=False):
        rolls = self.dice_qty .get()
        sides = self.die_faces.get()

        if self.group.mainframe.allow_odd.get() % 2 == 0 and sides % 2 != 0:
            self.die_faces.set(sides - 1)
            sides -= 1

        mod      = self.modifier .get()
        fmod     = self.finalmod .get()
        max_roll = sides
        min_roll = 1
        results  = []

        if self.group.mainframe.use_random_org.get():
            url = 'https://www.random.org/integers/?col={0}&num={0}&min={1}&max={2}&base=10&format=plain&rnd=new'
            url = url.format(rolls, min_roll, max_roll)
            try:
                resp = urlopen(url)
                results.extend([int(x) for x in str(resp.read().rstrip(), encoding='utf8').split('\t')])
                sleep(0.1)
            except:
                print('Failed to use random.org, falling back to CSPRNG!')

        if not results:
            csprng = SystemRandom()
            for i in range(rolls):
                roll = csprng.randint(min_roll, sides)
                results.append(roll)

        self.results = []
        for n in results:
            if n == max_roll:
                self.results.append(n * CRIT)
            elif n == min_roll:
                self.results.append(n * FAIL)
            else:
                self.results.append(n)

        self.apply_modifiers(True)

        self.history.append(self.create_hist_record())
        hist_index = len(self.history) - 1
        if single:
            for roller in self.group.rollers:
                if roller is not self:
                    roller.history.append(roller.create_hist_record())
            self.group.navigate_history(desired_index=hist_index)

        self.group.hist_index = hist_index
        self.name.set(self.name.get())

        self.group.mainframe.editmenu.entryconfigure(
            self.group.mainframe.editmenu.index('end'), command=lambda: self.roll(single=single))
        self.group.mainframe.bind_all('<Control-r>', lambda e: self.roll(single=single))

    def apply_modifiers(self, rolling=False):
        fmod = self.finalmod.get()
        dmod = self.modifier.get()
        dqty = self.dice_qty.get()

        formatted_results = []
        total = 0
        for n in self.results:
            if n > CRIT:
                n = int(n / CRIT)
                n = n + dmod
                formatted_results.append('\u25b2{}'.format(str(n)))
            elif 0 < n < 1:
                n = int(n / FAIL)
                n = n + dmod
                formatted_results.append('\u25bc{}'.format(str(n)))
            else:
                n = n + dmod
                formatted_results.append(str(n))
            total += n

        s = ' + '.join(formatted_results)
        s = '{} = {}'.format(total + fmod, s)

        if not rolling and self.history:
            self.history[self.group.hist_index]['modifier'    ] = dmod
            self.history[self.group.hist_index]['finalmod'    ] = fmod
            self.history[self.group.hist_index]['results_text'] = s

        self.results_text.set(s)
        self.group.maintain_result_widths()


if __name__ == '__main__':
    root = Tk()
    root.resizable(0,0)
    icon = PhotoImage(data=b'R0lGODlhIAAgAKECAAAAAD9IzP///////yH5BAEKAAMALAAAAAAgACAAAAJ5nI85AOoPGZyxLUvzNVL7roDeISJl9XQqhjorx07iecosHVNzPpI339v4gq4f0QSsaZTKDBPoTEJbtl5zOGIEttzu9hoCeMcBsI8cEAjGZi1ZzZ7C0Oi2mB63deF47nO/1vclJbjFN5hyJ3hYJsXwCBkp+TRZOYlQAAA7')
    root.iconphoto(root, icon)

    def on_closing():
        title = root.title()
        if '*' in title:
            if askyesno('Unsaved changes!', 'There are unsaved changes!\r\nWould you like to quit anyway?'):
                root.destroy()
        else:
            if askyesno('Quit?', 'Really quit?'):
                root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_closing)

    main = MainFrame(root)
    main.grid()
    root.mainloop()

