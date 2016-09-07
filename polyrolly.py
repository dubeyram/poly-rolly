#! /usr/bin/python3

from json    import dumps, load
from os.path import isfile
from random  import randint
from time    import sleep
from tkinter import \
        BooleanVar, \
        Button    , \
        Entry     , \
        Frame     , \
        IntVar    , \
        Label     , \
        LabelFrame, \
        Menu      , \
        Menubutton, \
        Spinbox   , \
        StringVar , \
        Tk
from tkinter.filedialog import askopenfilename, asksaveasfilename
from urllib .request    import urlopen


roller_groups = []

def maintain_group_indices():
    for group in roller_groups:
        group.index = roller_groups.index(group)
        group.grid(row=group.index)


class MainFrame(Frame):
    def __init__(self, master):
        Frame.__init__(self, master)

        self.fpath = ''

        self.use_random_org = BooleanVar()
        self.use_random_org.set(False)

        self.menubar = Menu(master)

        self.filemenu = Menu(self.menubar, tearoff=0, postcommand=maintain_group_indices)
        self.filemenu.add_command(label='New'       , command=self.reset_default_group                  , accelerator='Ctrl+N'      )
        self.filemenu.add_command(label='Load'      , command=self.load_config                          , accelerator='Ctrl+D'      )
        self.filemenu.add_command(label='Save'      , command=lambda: self.save_config(fpath=self.fpath), accelerator='Ctrl+S'      )
        self.filemenu.add_command(label='Save as...', command=self.save_config                          , accelerator='Ctrl+Shift+S')

        self.editmenu = Menu(self.menubar, tearoff=0)
        self.editmenu.add_checkbutton(label='Use random.org'    , variable=self.use_random_org)
        self.editmenu.add_command    (label='Repeat last action', accelerator='Ctrl+R'        )

        self.menubar.add_cascade(label='File', menu=self.filemenu)
        self.menubar.add_cascade(label='Edit', menu=self.editmenu)
        self.menubar.config(relief='flat')

        master.config(menu=self.menubar)

        self.reset_default_group()

        self.bind_all('<Control-n>'      , lambda e: self.reset_default_group()        )
        self.bind_all('<Control-d>'      , lambda e: self.load_config()                )
        self.bind_all('<Control-s>'      , lambda e: self.save_config(fpath=self.fpath))
        self.bind_all('<Control-Shift-S>', lambda e: self.save_config()                )

    def reset_default_group(self):
        self.clear_groups()
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
        fpath = askopenfilename(filetypes=[('JSON', '*.json'), ('All', '*.*')], defaultextension='.json')
        if not fpath or not isfile(fpath):
            return

        self.clear_groups()

        with open(fpath, 'r') as f:
            group_dict = load(f)

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
                h = len(roller.history) - 1
                r += 1

            group.navigate_history(desired_index=h)
            g += 1

        roller_groups.sort(key=lambda x: x.index)

        maintain_group_indices()
        for group in roller_groups:
            group.rollers.sort(key=lambda x: x.index)
            group.maintain_roller_indices()

        self.fpath = fpath

    def save_config(self, fpath=''):
        if not fpath:
            fpath = asksaveasfilename(filetypes=[('JSON', '*.json'), ('All', '*.*')], defaultextension='.json')
        if not fpath:
            return

        d1 = {}
        for group in roller_groups:
            group.maintain_roller_indices()
            d2 = {}
            d2['index'] = group.index
            d2['rollers'] = {}
            for roller in group.rollers:
                name = roller.name.get()
                if name in d2['rollers']:
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

        self.fpath = fpath


class RollerGroup(LabelFrame):
    def __init__(self, mainframe, index):
        LabelFrame.__init__(self, mainframe)

        self.mainframe     = mainframe
        self.index         = index
        self.hist_index    = 0
        self.rollers       = []
        self.control_frame = Frame(None)

        self.name = StringVar()

        self.name_entry    = Entry     (self.control_frame, bd=1, width=16, relief='solid', font=('Verdana', 12), textvariable=self.name)
        self.menu_btn      = Menubutton(self.control_frame, bd=1, text='\u25E2', relief='solid', font=('Courier',  8)                         )
        self.roll_btn      = Button    (self.control_frame, bd=1, text='\u21bb', relief='solid', font=('Verdana', 10), command=self.roll_group)
        self.hist_prev_btn = Button    (self.control_frame, bd=1, text='\u25c0', relief='solid', repeatdelay=250, repeatinterval=100, command=lambda: self.navigate_history(offset=-1))
        self.hist_next_btn = Button    (self.control_frame, bd=1, text='\u25b6', relief='solid', repeatdelay=250, repeatinterval=100, command=lambda: self.navigate_history(offset= 1))

        self.menu_btn.config(menu=self.create_menu())

        self.menu_btn     .grid(row=index, column=0, padx=(4, 0)              )
        self.name_entry   .grid(row=index, column=1, padx=(4, 0)              )
        self.hist_prev_btn.grid(row=index, column=2, padx=(4, 0) , sticky='ns')
        self.hist_next_btn.grid(row=index, column=3, padx=(0, 0) , sticky='ns')
        self.roll_btn     .grid(row=index, column=4, padx=(4, 4) , sticky='ns')

        self.config(labelwidget=self.control_frame, text='Group {}'.format(self.index + 1))
        self.name.set('Group {}'.format(len(roller_groups) + 1))
        self.grid(row=index, padx=4, pady=4, sticky='w')

    def create_menu(self):
        menu = Menu(self.menu_btn, tearoff=0, postcommand=maintain_group_indices)

        menu.add_command(label='Add'   , command=       self.add_group             )
        menu.add_command(label='Clone' , command=lambda:self.add_group (clone=True))
        menu.add_command(label='Up'    , command=lambda:self.move_group(offset=-1) )
        menu.add_command(label='Down'  , command=lambda:self.move_group(offset= 1) )
        menu.add_command(label='Remove', command=       self.remove_group          )

        return menu

    def add_group(self, clone=False):
        destination_index = self.index + 1

        group = RollerGroup(self.mainframe, destination_index)
        roller_groups.insert(group.index, group)

        for i in range(destination_index, len(roller_groups)):
            roller_groups[i].grid(row=i + 1)

        if clone:
            group.name.set(self.name.get())
            for roller in self.rollers:
                new_roller = Roller(group, self.rollers.index(roller))
                new_roller.name     .set(roller.name     .get())
                new_roller.dice_qty .set(roller.dice_qty .get())
                new_roller.die_faces.set(roller.die_faces.get())
                new_roller.modifier .set(roller.modifier .get())
                new_roller.finalmod .set(roller.finalmod .get())
                group.rollers.append(new_roller)
        else:
            group.rollers.append(Roller(group, 0))

        self.mainframe.editmenu.entryconfigure(1, command=lambda: self.add_group(clone=clone))
        self.mainframe.bind_all('<Control-r>', lambda e: self.add_group(clone=clone))

    def move_group(self, offset=0, destination_index=0):
        if not destination_index:
            destination_index = self.index + offset

        if destination_index >= 0:
            group = roller_groups.pop(self.index)
            roller_groups.insert(destination_index, group)

        maintain_group_indices()

        self.mainframe.editmenu.entryconfigure(1, command=lambda: self.move_group(offset=offset))
        self.mainframe.bind_all('<Control-r>', lambda e: self.move_group(offset=offset))

    def remove_group(self, override=False):
        if len(roller_groups) > 1 or override:
            self.grid_remove()
            roller_groups.remove(self)

    def maintain_roller_indices(self):
        for roller in self.rollers:
            roller.index = self.rollers.index(roller)
            roller.grid(row=roller.index)

    def roll_group(self):
        for roller in self.rollers:
            roller.roll()

        self.mainframe.editmenu.entryconfigure(1, command=lambda: self.roll_group())
        self.mainframe.bind_all('<Control-r>', lambda e: self.roll_group())

    def navigate_history(self, offset=0, desired_index=0):
        if not desired_index:
            desired_index = self.hist_index + offset

        if desired_index >= 0 and desired_index < len(self.rollers[0].history):
            for roller in self.rollers:
                roller.results.set(roller.history[desired_index])

            self.hist_index = desired_index

        self.maintain_result_widths()

    def maintain_result_widths(self):
        for roller in self.rollers:
            w = len(roller.results.get())
            if w > 80:
                w = 80
            roller.results_entry.config(width=w)


class Roller(Frame):
    def __init__(self, group, index):
        Frame.__init__(self, group)

        self.group   = group
        self.index   = index
        self.history = []

        self.name      = StringVar()
        self.dice_qty  = IntVar()
        self.die_faces = IntVar()
        self.modifier  = IntVar()
        self.finalmod  = IntVar()
        self.results   = StringVar()

        default_font        = ('Courier', 14)
        self.menu_btn       = Menubutton(self, bd=1, text='\u25E2', relief='solid', font=('Courier',  8)                                        )
        self.roll_btn       = Button    (self, bd=1, text='\u21bb', relief='solid', font=('Verdana', 10), command=lambda: self.roll(single=True))
        self.name_entry     = Entry     (self, bd=1, width=16, relief='solid', textvariable=self.name   , font=('Verdana' , 12)                                )
        self.results_entry  = Entry     (self, bd=0, width=0 , relief='solid', textvariable=self.results, state='readonly', font=default_font, justify='center')
        self.dice_qty_spin  = Spinbox   (self, bd=0, to=99 , from_=1  , width=2, relief='solid', state='readonly', textvariable=self.dice_qty , font=default_font             )
        self.die_faces_spin = Spinbox   (self, bd=0, to=100, from_=2  , width=3, relief='solid', state='readonly', textvariable=self.die_faces, font=default_font, increment=2)
        self.modifier_spin  = Spinbox   (self, bd=0, to=100, from_=-99, width=3, relief='solid', state='readonly', textvariable=self.modifier , font=default_font             )
        self.finalmod_spin  = Spinbox   (self, bd=0, to=100, from_=-99, width=3, relief='solid', state='readonly', textvariable=self.finalmod , font=default_font             )
        self.dice_lbl       = Label     (self, text=' \u00d7 (d', font=default_font)
        self.modifier_lbl   = Label     (self, text='\u002b'    , font=default_font)
        self.finalmod_lbl   = Label     (self, text='\u002b'    , font=default_font)
        self.close_lbl      = Label     (self, text=')'         , font=default_font)

        self.menu_btn.config(menu=self.create_menu())

        self.menu_btn      .grid(row=index, column=0 , padx=(4, 0))
        self.name_entry    .grid(row=index, column=1 , padx=(4, 0))
        self.dice_qty_spin .grid(row=index, column=2 , padx=(4, 0))
        self.dice_lbl      .grid(row=index, column=3 , padx=(0, 0))
        self.die_faces_spin.grid(row=index, column=4 , padx=(0, 0))
        self.modifier_lbl  .grid(row=index, column=5 , padx=(6, 6))
        self.modifier_spin .grid(row=index, column=6 , padx=(0, 0))
        self.close_lbl     .grid(row=index, column=7 , padx=(0, 0))
        self.roll_btn      .grid(row=index, column=8 , padx=(4, 0))
        self.results_entry .grid(row=index, column=9 , padx=(4, 0))
        self.finalmod_lbl  .grid(row=index, column=10, padx=(6, 6))
        self.finalmod_spin .grid(row=index, column=11, padx=(0, 4))

        self.name     .set('Roller {}'.format(len(self.group.rollers) + 1))
        self.die_faces.set(10)
        self.results  .set('0')

        self.grid(row=index, sticky='w', pady=4)

    def create_menu(self):
        menu = Menu(self.menu_btn, tearoff=0, postcommand=self.group.maintain_roller_indices)

        menu.add_command(label='Add'   , command=       self.add_roller             )
        menu.add_command(label='Clone' , command=lambda:self.add_roller (clone=True))
        menu.add_command(label='Up'    , command=lambda:self.move_roller(offset=-1) )
        menu.add_command(label='Down'  , command=lambda:self.move_roller(offset= 1) )
        menu.add_command(label='Remove', command=       self.remove_roller          )

        return menu

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

        for h in self.history:
            roller.history.append('0')

        self.group.mainframe.editmenu.entryconfigure(1, command=lambda: self.add_roller(clone=clone))
        self.group.mainframe.bind_all('<Control-r>', lambda e: self.add_roller(clone=clone))

    def move_roller(self, offset=0, destination_index=0):
        if not destination_index:
            destination_index = self.index + offset

        if destination_index >= 0:
            roller = self.group.rollers.pop(self.index)
            self.group.rollers.insert(destination_index, roller)

        self.group.maintain_roller_indices()

        self.group.mainframe.editmenu.entryconfigure(1, command=lambda: self.move_roller(offset=offset))
        self.group.mainframe.bind_all('<Control-r>', lambda e: self.move_roller(offset=offset))

    def remove_roller(self):
        if len(self.group.rollers) > 1:
            self.grid_remove()
            self.group.rollers.remove(self)

    def roll(self, single=False):
        rolls = self.dice_qty .get()
        sides = self.die_faces.get()
        mod   = self.modifier .get()
        fmod  = self.finalmod .get()

        max_roll = sides + mod
        min_roll = 1     + mod

        result = []
        total  = 0

        if self.group.mainframe.use_random_org.get():
            url = 'https://www.random.org/integers/?col={0}&num={0}&min={1}&max={2}&base=10&format=plain&rnd=new'
            url = url.format(rolls, min_roll, max_roll)
            try:
                resp = urlopen(url)
                result.extend([int(x) for x in resp.read().rstrip().split('\t')])
                sleep(0.1)
            except:
                pass

        if not result:
            for i in range(rolls):
                roll   = randint(1, sides) + mod
                total += roll
                result.append(roll)

        str_result = []
        for n in result:
            if n == max_roll:
                str_result.append('\u25b2{}'.format(n))
            elif n == min_roll:
                str_result.append('\u25bc{}'.format(n))
            else:
                str_result.append(str(n))

        s = ' + '.join(str_result)
        if  ' + ' in s or fmod != 0:
            s = '{} = {}'.format(total + fmod, s)
        self.results.set(s)

        self.history.append(s)
        if single:
            for roller in self.group.rollers:
                if roller is not self:
                    try:
                        h = roller.history[-1]
                    except IndexError:
                        h = '0'
                    roller.history.append(h)
        self.group.hist_index = len(self.history) - 1

        self.group.maintain_result_widths()

        self.group.mainframe.editmenu.entryconfigure(1, command=lambda: self.roll(single=single))
        self.group.mainframe.bind_all('<Control-r>', lambda e: self.roll(single=single))


if __name__ == '__main__':
    root = Tk()
    root.title('Poly Rolly')

    main = MainFrame(root)
    main.grid()

    root.mainloop()
