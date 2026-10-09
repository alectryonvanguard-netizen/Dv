from kivy.app import App
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.graphics import Color, Line, Rectangle
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.uix.image import Image
from kivy.uix.video import Video
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.modalview import ModalView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.textinput import TextInput
from kivy.utils import get_color_from_hex
import os

# Optional Android helpers
try:
    from plyer import filechooser
except Exception:
    filechooser = None

try:
    from jnius import autoclass
    from android import activity
    ANDROID_PICKER_AVAILABLE = True
except Exception:
    autoclass = None
    activity = None
    ANDROID_PICKER_AVAILABLE = False

BG = "#050508"
PANEL = "#101018"
CYAN = "#00F5E9"
PINK = "#FF286F"
PURPLE = "#965CFF"
WHITE = "#FFFFFF"
GREY = "#92929D"

VIDEO_EXTENSIONS = (".mp4", ".mkv", ".mov", ".avi", ".webm", ".3gp", ".m4v")
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")


def rgba(value):
    return get_color_from_hex(value)


class NeonSpinner(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.angle = 0
        self.bind(pos=self.draw_spinner, size=self.draw_spinner)
        Clock.schedule_interval(self.rotate, 1 / 30)

    def rotate(self, dt):
        self.angle = (self.angle + 8) % 360
        self.draw_spinner()

    def draw_spinner(self, *args):
        self.canvas.clear()
        with self.canvas:
            Color(*rgba(CYAN))
            Line(
                circle=(
                    self.center_x, self.center_y,
                    min(self.width, self.height) * 0.35,
                    self.angle, self.angle + 255
                ),
                width=dp(3)
            )
            Color(*rgba(PINK))
            Line(
                circle=(
                    self.center_x, self.center_y,
                    min(self.width, self.height) * 0.23,
                    -self.angle, -self.angle + 95
                ),
                width=dp(2)
            )


class BootScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = FloatLayout()
        self.add_widget(layout)

        with layout.canvas.before:
            Color(*rgba(BG))
            self.bg_rect = Rectangle(pos=layout.pos, size=layout.size)

        layout.bind(
            pos=lambda obj, value: setattr(self.bg_rect, "pos", value),
            size=lambda obj, value: setattr(self.bg_rect, "size", value)
        )

        self.logo = FloatLayout(
            size_hint=(0.8, 0.34),
            pos_hint={"center_x": 0.5, "center_y": 0.61}
        )
        layout.add_widget(self.logo)

        for colour, offset_x, offset_y in [
            (PINK, dp(5), -dp(3)),
            (CYAN, -dp(5), dp(3)),
            (WHITE, 0, 0)
        ]:
            letter = Label(
                text="S", font_size="150sp", bold=True,
                color=rgba(colour), size_hint=(1, 1),
                pos_hint={"center_x": 0.5, "center_y": 0.5}
            )
            letter.font_size = min(Window.width * 0.36, Window.height * 0.20)
            letter.x += offset_x
            letter.y += offset_y
            self.logo.add_widget(letter)

        layout.add_widget(Label(
            text="SAM NG", font_size="22sp", bold=True,
            color=rgba(WHITE), size_hint=(0.8, 0.06),
            pos_hint={"center_x": 0.5, "center_y": 0.40}
        ))
        layout.add_widget(NeonSpinner(
            size_hint=(None, None), size=(dp(70), dp(70)),
            pos_hint={"center_x": 0.5, "center_y": 0.31}
        ))
        self.progress = ProgressBar(
            max=100, value=0, size_hint=(0.62, None),
            height=dp(8), pos_hint={"center_x": 0.5, "center_y": 0.22}
        )
        layout.add_widget(self.progress)
        self.value = 0
        Clock.schedule_interval(self.advance, 0.04)

    def advance(self, dt):
        self.value += 1.2
        self.progress.value = min(self.value, 100)
        if self.value >= 100:
            Clock.unschedule(self.advance)
            self.manager.current = "home"
            return False


class HomeScreen(Screen):
    PICKER_REQUEST_CODE = 2468

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_path = None
        self.posts = []
        self.active_tab = "For You"
        self.active_page = "Home"
        self.picker_popup = None
        self.is_liked = False
        self.is_saved = False
        self.comments = []
        self.dark_mode = True
        self.feed_scroll = None

        # Bind Android activity results once, if running on Android with PyJNIus.
        if ANDROID_PICKER_AVAILABLE:
            try:
                activity.bind(on_activity_result=self.on_android_activity_result)
            except Exception:
                pass

        outer = BoxLayout(orientation="vertical", spacing=0)
        self.add_widget(outer)

        with outer.canvas.before:
            self.background_color_instruction = Color(*rgba(BG))
            self.background = Rectangle(pos=outer.pos, size=outer.size)
        outer.bind(
            pos=lambda obj, value: setattr(self.background, "pos", value),
            size=lambda obj, value: setattr(self.background, "size", value)
        )

        top = BoxLayout(
            size_hint_y=None, height=dp(58),
            padding=(dp(5), dp(5)), spacing=dp(1)
        )
        self.top_tabs_bar = top
        outer.add_widget(top)
        self.tab_buttons = {}

        for name in ("STEM", "Following", "For You"):
            button = Button(
                text=name, font_size="13sp", bold=True,
                background_normal="", background_color=rgba(PANEL),
                color=rgba(WHITE if name == "For You" else GREY)
            )
            button.bind(on_release=lambda btn, n=name: self.change_tab(n))
            top.add_widget(button)
            self.tab_buttons[name] = button

        search_button = Button(
            text="Search", size_hint_x=None, width=dp(68),
            font_size="12sp", background_normal="",
            background_color=rgba(BG), color=rgba(CYAN)
        )
        search_button.bind(on_release=self.search)
        top.add_widget(search_button)

        self.feed = BoxLayout(
            orientation="vertical", padding=(dp(16), dp(12)),
            spacing=dp(10)
        )
        outer.add_widget(self.feed)

        nav = BoxLayout(
            size_hint_y=None, height=dp(72),
            spacing=dp(2), padding=(dp(3), dp(4))
        )
        self.bottom_nav_bar = nav
        outer.add_widget(nav)
        self.nav_buttons = {}

        for name in ("Home", "Friends", "Create", "Inbox", "Profile"):
            button = Button(
                text=name, font_size="11sp", bold=True,
                background_normal="", background_color=rgba("#0A0A10"),
                color=rgba(CYAN if name == "Home" else GREY)
            )
            button.bind(on_release=lambda btn, n=name: self.navigate(n))
            nav.add_widget(button)
            self.nav_buttons[name] = button

        self.show_feed()

    def clear_feed(self):
        self.feed.clear_widgets()

    def show_feed(self):
        self.clear_feed()
        self.feed.add_widget(Label(
            text="SAM NG DVSG SG", color=rgba(CYAN), font_size="12sp",
            bold=True, size_hint_y=None, height=dp(25), halign="left"
        ))
        self.feed.add_widget(Label(
            text="S íś fôř ýöü.", color=rgba(WHITE),
            font_size="21sp", bold=True, size_hint_y=None,
            height=dp(38), halign="left"
        ))

        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        posts = BoxLayout(orientation="vertical", size_hint_y=None,
                          spacing=dp(12), padding=(0, 0, 0, dp(12)))
        posts.bind(minimum_height=posts.setter("height"))
        scroll.add_widget(posts)
        self.feed.add_widget(scroll)
        self.feed_scroll = posts

        if not self.posts:
            empty = BoxLayout(orientation="vertical", size_hint_y=None,
                              height=dp(210), spacing=dp(12), padding=dp(18))
            empty.add_widget(Label(
                text="Your feed starts here", color=rgba(GREY),
                font_size="16sp", size_hint_y=None, height=dp(40)
            ))
            empty.add_widget(Label(
                text="Tap Create to add a photo or video.",
                color=rgba("#666672"), font_size="12sp",
                size_hint_y=None, height=dp(34)
            ))
            create_button = Button(
                text="+ Create a post", size_hint_y=None, height=dp(46),
                background_normal="", background_color=rgba(PANEL),
                color=rgba(CYAN)
            )
            create_button.bind(on_release=lambda *_: self.pick_media())
            empty.add_widget(create_button)
            posts.add_widget(empty)
            return

        for post_path in reversed(self.posts):
            if os.path.isfile(post_path):
                posts.add_widget(self.make_post_card(post_path, show_actions=True))

    def make_post_card(self, path, show_actions=True):
        card = BoxLayout(orientation="vertical", size_hint_y=None,
                         spacing=dp(8), padding=dp(8))
        card.bind(minimum_height=card.setter("height"))
        header = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        avatar = Label(text="S", size_hint_x=None, width=dp(38),
                       bold=True, color=rgba(BG), font_size="18sp")
        with avatar.canvas.before:
            Color(*rgba(CYAN))
            avatar_bg = Rectangle(pos=avatar.pos, size=avatar.size)
        avatar.bind(pos=lambda w, v: setattr(avatar_bg, "pos", v),
                    size=lambda w, v: setattr(avatar_bg, "size", v))
        header.add_widget(avatar)
        header.add_widget(Label(text="Sam Ng", color=rgba(WHITE), bold=True,
                                halign="left"))
        card.add_widget(header)
        extension = os.path.splitext(path)[1].lower()
        try:
            if extension in VIDEO_EXTENSIONS:
                media = Video(source=path, state="play", options={"eos": "loop"},
                              allow_stretch=True, keep_ratio=True,
                              size_hint_y=None, height=dp(350))
                media.bind(on_load=lambda widget, *_: setattr(widget, "state", "play"))
                media.bind(on_error=lambda *_: self.show_message(
                    "Video playback", "This video format may not be supported by your phone."))
            else:
                media = Image(source=path, allow_stretch=True, keep_ratio=True,
                              size_hint_y=None, height=dp(350))
            card.add_widget(media)
        except Exception as error:
            card.add_widget(Label(text="Cannot display this media: " + str(error),
                                  color=rgba(PINK), size_hint_y=None, height=dp(70)))
        if show_actions:
            actions = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(4))
            like_text = ("♥ Liked" if self.is_liked else "♡ Like")
            like_button = Button(text=like_text, background_normal="",
                                 background_color=rgba(PANEL),
                                 color=rgba(PINK if self.is_liked else WHITE), font_size="12sp")
            like_button.bind(on_release=lambda *_: self.toggle_like())
            share_button = Button(text="↗ Share", background_normal="",
                                  background_color=rgba(PANEL), color=rgba(CYAN), font_size="12sp")
            share_button.bind(on_release=lambda *_: self.share_post(path))
            save_button = Button(text=("✓ Saved" if self.is_saved else "▣ Save"),
                                 background_normal="", background_color=rgba(PANEL),
                                 color=rgba(CYAN if self.is_saved else WHITE), font_size="12sp")
            save_button.bind(on_release=lambda *_: self.toggle_save())
            comment_button = Button(text="☰ Comment", background_normal="",
                                    background_color=rgba(PANEL), color=rgba(WHITE), font_size="12sp")
            comment_button.bind(on_release=lambda *_: self.open_comments())
            for b in (like_button, share_button, save_button, comment_button):
                actions.add_widget(b)
            card.add_widget(actions)
            if self.comments:
                card.add_widget(Label(text=f"{len(self.comments)} comment(s)",
                                      color=rgba(GREY), size_hint_y=None, height=dp(24),
                                      halign="left"))
        return card

    def change_tab(self, name):
        self.active_tab = name
        for tab, button in self.tab_buttons.items():
            button.color = rgba(WHITE if tab == name else GREY)
        if name == "For You":
            self.show_feed()
        elif name == "Following":
            self.show_message("Following", "Posts from followed accounts will appear here.")
        else:
            self.show_message("STEM", "Science, technology, engineering and mathematics.")

    def set_profile_chrome(self, on_profile):
        """Hide both navigation bars on Profile; restore them elsewhere."""
        if on_profile:
            self.top_tabs_bar.height = 0
            self.top_tabs_bar.opacity = 0
            self.top_tabs_bar.disabled = True
            self.bottom_nav_bar.height = 0
            self.bottom_nav_bar.opacity = 0
            self.bottom_nav_bar.disabled = True
        else:
            self.top_tabs_bar.height = dp(58)
            self.top_tabs_bar.opacity = 1
            self.top_tabs_bar.disabled = False
            self.bottom_nav_bar.height = dp(72)
            self.bottom_nav_bar.opacity = 1
            self.bottom_nav_bar.disabled = False

    def navigate(self, name):
        self.active_page = name
        self.set_profile_chrome(name == "Profile")
        for page, button in self.nav_buttons.items():
            button.color = rgba(CYAN if page == name else GREY)
        if name == "Home":
            self.change_tab("For You")
        elif name == "Create":
            self.pick_media()
        elif name == "Friends":
            self.show_message("Friends", "Your friends will appear here when friend connections are added.")
        elif name == "Inbox":
            self.show_message("Inbox", "Your messages will appear here when messaging is connected.")
        elif name == "Profile":
            self.show_profile()

    def show_profile(self):
        self.active_page = "Profile"
        self.set_profile_chrome(True)
        self.clear_feed()
        top = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        back = Button(text="‹", size_hint_x=None, width=dp(44),
                      font_size="30sp", background_normal="",
                      background_color=rgba(PANEL), color=rgba(CYAN))
        back.bind(on_release=lambda *_: self.navigate("Home"))
        top.add_widget(back)
        top.add_widget(Label(text="PROFILE", color=rgba(CYAN), font_size="20sp",
                             bold=True, halign="left"))
        dots = Button(text="⋮", size_hint_x=None, width=dp(48),
                      font_size="28sp", background_normal="",
                      background_color=rgba(PANEL), color=rgba(WHITE))
        dots.bind(on_release=lambda *_: self.open_profile_menu())
        top.add_widget(dots)
        self.feed.add_widget(top)

        profile_scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        body = BoxLayout(orientation="vertical", size_hint_y=None,
                         spacing=dp(12), padding=(dp(4), dp(8), dp(4), dp(12)))
        body.bind(minimum_height=body.setter("height"))
        profile_scroll.add_widget(body)
        self.feed.add_widget(profile_scroll)

        profile_header = BoxLayout(orientation="vertical", size_hint_y=None,
                                   height=dp(190), spacing=dp(8), padding=dp(8))
        avatar = Label(text="S", size_hint=(None, None), size=(dp(84), dp(84)),
                       pos_hint={"center_x": 0.5}, font_size="34sp", bold=True,
                       color=rgba(BG))
        with avatar.canvas.before:
            Color(*rgba(CYAN))
            avatar_rect = Rectangle(pos=avatar.pos, size=avatar.size)
        avatar.bind(pos=lambda w, v: setattr(avatar_rect, "pos", v),
                    size=lambda w, v: setattr(avatar_rect, "size", v))
        profile_header.add_widget(avatar)
        profile_header.add_widget(Label(text="Sam Ng", color=rgba(WHITE),
                                        font_size="20sp", bold=True,
                                        size_hint_y=None, height=dp(32)))
        profile_header.add_widget(Label(text="Your profile and your posts", color=rgba(GREY),
                                        font_size="12sp", size_hint_y=None, height=dp(24)))
        body.add_widget(profile_header)
        body.add_widget(Label(text="YOUR VIDEOS & POSTS", color=rgba(CYAN),
                              bold=True, size_hint_y=None, height=dp(36), halign="left"))
        valid_posts = [path for path in self.posts if os.path.isfile(path)]
        if valid_posts:
            for post_path in reversed(valid_posts):
                body.add_widget(self.make_post_card(post_path, show_actions=True))
        else:
            body.add_widget(Label(text="Your posts will appear here after you create one.",
                                  color=rgba(GREY), size_hint_y=None, height=dp(90)))

    def open_profile_menu(self):
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        popup = Popup(title="Profile menu", content=content,
                      size_hint=(0.86, None), height=dp(220))
        about = Button(text="About Sam Ng", size_hint_y=None, height=dp(48),
                       background_normal="", background_color=rgba(PANEL), color=rgba(CYAN))
        settings = Button(text="Settings", size_hint_y=None, height=dp(48),
                          background_normal="", background_color=rgba(PANEL), color=rgba(WHITE))
        close = Button(text="Close", size_hint_y=None, height=dp(42))
        about.bind(on_release=lambda *_: (popup.dismiss(), self.show_about()))
        settings.bind(on_release=lambda *_: (popup.dismiss(), self.show_settings()))
        close.bind(on_release=popup.dismiss)
        for b in (about, settings, close):
            content.add_widget(b)
        popup.open()

    def show_about(self):
        self.set_profile_chrome(True)
        self.clear_feed()
        top = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        top.add_widget(Label(text="ABOUT SAM NG", color=rgba(CYAN), font_size="20sp", bold=True))
        back = Button(text="Profile", size_hint_x=None, width=dp(84),
                      background_normal="", background_color=rgba(PANEL), color=rgba(WHITE))
        back.bind(on_release=lambda *_: self.show_profile())
        top.add_widget(back)
        self.feed.add_widget(top)
        self.feed.add_widget(Label(text="Sam Ng is a social app prototype for sharing photos and videos.\nVersion 0.4\nPosts are stored locally on this device; online accounts and sharing require a backend.",
                                   color=rgba(GREY), halign="center", valign="top"))

    def show_settings(self):
        self.clear_feed()
        top = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        top.add_widget(Label(text="SETTINGS", color=rgba(CYAN), font_size="21sp", bold=True))
        back = Button(text="Profile", size_hint_x=None, width=dp(84),
                      background_normal="", background_color=rgba(PANEL), color=rgba(WHITE))
        back.bind(on_release=lambda *_: self.show_profile())
        top.add_widget(back)
        self.feed.add_widget(top)
        self.feed.add_widget(Label(text="Appearance", color=rgba(CYAN), bold=True,
                                   size_hint_y=None, height=dp(34), halign="left"))
        dark_button = Button(text=("Dark mode: ON" if self.dark_mode else "Dark mode: OFF"),
                             size_hint_y=None, height=dp(48), background_normal="",
                             background_color=rgba(PANEL), color=rgba(WHITE))
        dark_button.bind(on_release=lambda *_: self.toggle_dark_mode())
        self.feed.add_widget(dark_button)
        self.feed.add_widget(Label(text="Security & privacy", color=rgba(CYAN), bold=True,
                                   size_hint_y=None, height=dp(34), halign="left"))
        security = Button(text="Security options", size_hint_y=None, height=dp(46),
                          background_normal="", background_color=rgba(PANEL), color=rgba(WHITE))
        security.bind(on_release=lambda *_: self.show_message(
            "Security", "This prototype does not yet have online accounts. Before launch, add secure sign-in, account recovery, and session protection."))
        privacy = Button(text="Privacy policy", size_hint_y=None, height=dp(46),
                         background_normal="", background_color=rgba(PANEL), color=rgba(WHITE))
        privacy.bind(on_release=lambda *_: self.show_message(
            "Privacy policy", "Prototype policy: selected media is used to display posts in this app. Posts are not uploaded to a server by this prototype. A full privacy policy must be added before online publishing."))
        terms = Button(text="Community & safety", size_hint_y=None, height=dp(46),
                       background_normal="", background_color=rgba(PANEL), color=rgba(WHITE))
        terms.bind(on_release=lambda *_: self.show_message(
            "Community & safety", "Be respectful, post only content you have permission to share, and report harmful content. Reporting tools are not connected in this prototype."))
        for b in (security, privacy, terms):
            self.feed.add_widget(b)

    def toggle_dark_mode(self):
        global BG, PANEL, WHITE, GREY, CYAN, PINK
        self.dark_mode = not self.dark_mode
        if self.dark_mode:
            BG, PANEL, WHITE, GREY, CYAN, PINK = (
                "#050508", "#101018", "#FFFFFF", "#92929D", "#00F5E9", "#FF286F"
            )
        else:
            BG, PANEL, WHITE, GREY, CYAN, PINK = (
                "#F4F5F8", "#FFFFFF", "#171722", "#666672", "#007F83", "#D91B59"
            )
        try:
            self.background_color_instruction.rgba = rgba(BG)
        except Exception:
            pass
        self.show_settings()

    def toggle_like(self):
        self.is_liked = not self.is_liked
        self.show_feed()

    def toggle_save(self):
        self.is_saved = not self.is_saved
        self.show_feed()

    def share_post(self, path):
        self.show_message("Share", "Selected post file:\n" + os.path.basename(path) + "\nSystem sharing will be connected in a later version.")

    def open_comments(self):
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(10))
        entry = TextInput(hint_text="Write a comment...", multiline=True, size_hint_y=None, height=dp(100))
        content.add_widget(entry)
        buttons = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        popup = Popup(title="Comments", content=content, size_hint=(0.9, None), height=dp(240))
        cancel = Button(text="Cancel")
        post = Button(text="Post comment", background_normal="", background_color=rgba(PANEL), color=rgba(CYAN))
        cancel.bind(on_release=popup.dismiss)
        def submit_comment(*_):
            value = entry.text.strip()
            if value:
                self.comments.append(value)
                popup.dismiss()
                self.show_feed()
            else:
                entry.hint_text = "Type a comment first"
        post.bind(on_release=submit_comment)
        buttons.add_widget(cancel)
        buttons.add_widget(post)
        content.add_widget(buttons)
        popup.open()

    def show_message(self, title, description):
        self.clear_feed()
        self.feed.add_widget(Label(
            text=title, color=rgba(CYAN), font_size="23sp",
            bold=True, size_hint_y=None, height=dp(55)
        ))
        self.feed.add_widget(Label(
            text=description, color=rgba(GREY), font_size="14sp",
            halign="center", valign="top"
        ))

    def pick_media(self):
        """Open Android's native Photos picker sheet, then import the result."""
        if ANDROID_PICKER_AVAILABLE:
            try:
                Intent = autoclass("android.content.Intent")
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                intent = Intent(Intent.ACTION_GET_CONTENT)
                intent.setType("*/*")
                intent.addCategory(Intent.CATEGORY_OPENABLE)
                mime_types = ["image/*", "video/*"]
                intent.putExtra(Intent.EXTRA_MIME_TYPES, mime_types)
                intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                PythonActivity.mActivity.startActivityForResult(
                    intent, self.PICKER_REQUEST_CODE
                )
                return
            except Exception as error:
                self.show_message(
                    "Could not open Photos",
                    "Android could not open its media picker: " + str(error)
                )
                return

        self.open_recent_media_sheet()

    def open_recent_media_sheet(self):
        sheet = ModalView(size_hint=(1, 0.80), pos_hint={"x": 0, "y": 0},
                          auto_dismiss=True, background_color=(0, 0, 0, 0.72))
        self.picker_popup = sheet
        panel = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        with panel.canvas.before:
            Color(*rgba(PANEL))
            panel_bg = Rectangle(pos=panel.pos, size=panel.size)
        panel.bind(pos=lambda w, v: setattr(panel_bg, "pos", v),
                   size=lambda w, v: setattr(panel_bg, "size", v))

        header = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        title = Label(text="Recent photos and videos", color=rgba(WHITE),
                      bold=True, font_size="17sp", halign="left")
        close = Button(text="✕", size_hint_x=None, width=dp(44),
                       background_normal="", background_color=rgba("#252532"),
                       color=rgba(WHITE))
        close.bind(on_release=lambda *_: sheet.dismiss())
        header.add_widget(title)
        header.add_widget(close)
        panel.add_widget(header)
        panel.add_widget(Label(
            text="Choose media below. It stays inside Sam Ng.", color=rgba(GREY),
            size_hint_y=None, height=dp(25), font_size="12sp"
        ))

        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        grid = GridLayout(cols=2, spacing=dp(8), padding=(0, 0, 0, dp(10)),
                          size_hint_y=None, row_default_height=dp(150),
                          row_force_default=True)
        grid.bind(minimum_height=grid.setter("height"))
        scroll.add_widget(grid)
        panel.add_widget(scroll)
        sheet.add_widget(panel)

        media_items = self.get_recent_media_items()
        if not media_items:
            grid.add_widget(Label(
                text="No recent photos or videos found.\n\nCheck that Pydroid has photo/media access, then reopen Create.",
                color=rgba(GREY), size_hint_y=None, height=dp(150)
            ))
        else:
            for item in media_items:
                tile = BoxLayout(orientation="vertical", spacing=dp(4), padding=dp(5))
                with tile.canvas.before:
                    Color(*rgba("#1B1B27"))
                    tile_bg = Rectangle(pos=tile.pos, size=tile.size)
                tile.bind(pos=lambda w, v, r=tile_bg: setattr(r, "pos", v),
                          size=lambda w, v, r=tile_bg: setattr(r, "size", v))
                preview = FloatLayout(size_hint_y=1)
                if item.get("path") and item["kind"] == "photo":
                    try:
                        preview.add_widget(Image(source=item["path"], allow_stretch=True,
                                                 keep_ratio=True))
                    except Exception:
                        preview.add_widget(Label(text="PHOTO", color=rgba(CYAN)))
                else:
                    icon_text = "▶ VIDEO" if item["kind"] == "video" else "▧ PHOTO"
                    preview.add_widget(Label(text=icon_text, color=rgba(CYAN),
                                             bold=True, font_size="18sp"))
                tile.add_widget(preview)
                name = item.get("name", "Media file")
                if len(name) > 25:
                    name = name[:22] + "..."
                choose = Button(text=name, size_hint_y=None, height=dp(36),
                                background_normal="", background_color=rgba(PANEL),
                                color=rgba(WHITE), font_size="11sp")
                choose.bind(on_release=lambda *_args, it=item: self.choose_recent_media(it, sheet))
                tile.add_widget(choose)
                grid.add_widget(tile)

        sheet.open()

    def get_recent_media_items(self):
        """Read recent media from Android MediaStore; scan common folders as fallback."""
        items = []
        seen = set()

        if ANDROID_PICKER_AVAILABLE:
            cursor = None
            try:
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                MediaStoreImages = autoclass("android.provider.MediaStore$Images$Media")
                MediaStoreVideos = autoclass("android.provider.MediaStore$Video$Media")
                MediaColumns = autoclass("android.provider.MediaStore$MediaColumns")
                activity_instance = PythonActivity.mActivity
                resolver = activity_instance.getContentResolver()
                for base_uri, kind in [
                    (MediaStoreImages.EXTERNAL_CONTENT_URI, "photo"),
                    (MediaStoreVideos.EXTERNAL_CONTENT_URI, "video")
                ]:
                    cursor = None
                    try:
                        columns = [MediaColumns._ID, MediaColumns.DISPLAY_NAME,
                                   MediaColumns.DATE_ADDED]
                        cursor = resolver.query(base_uri, columns, None, None,
                                                MediaColumns.DATE_ADDED + " DESC")
                        if cursor is None:
                            continue
                        id_col = cursor.getColumnIndex(MediaColumns._ID)
                        name_col = cursor.getColumnIndex(MediaColumns.DISPLAY_NAME)
                        count = 0
                        while cursor.moveToNext() and count < 60:
                            media_id = cursor.getLong(id_col)
                            display_name = str(cursor.getString(name_col) or ("Photo" if kind == "photo" else "Video"))
                            content_uri = str(base_uri) + "/" + str(media_id)
                            if content_uri not in seen:
                                items.append({"name": display_name, "kind": kind,
                                              "uri": content_uri})
                                seen.add(content_uri)
                                count += 1
                    except Exception:
                        pass
                    finally:
                        try:
                            if cursor is not None:
                                cursor.close()
                        except Exception:
                            pass
            except Exception:
                pass

        if not items:
            roots = [
                "/storage/emulated/0/DCIM/Camera",
                "/storage/emulated/0/DCIM",
                "/storage/emulated/0/Pictures",
                "/storage/emulated/0/Movies",
                "/storage/emulated/0/Download",
                "/storage/emulated/0/WhatsApp/Media/WhatsApp Images",
                "/storage/emulated/0/WhatsApp/Media/WhatsApp Video",
                os.path.expanduser("~/DCIM"), os.path.expanduser("~/Pictures"),
                os.path.expanduser("~/Download")
            ]
            found = []
            for root in roots:
                if not os.path.isdir(root):
                    continue
                try:
                    for current, dirs, files in os.walk(root):
                        dirs[:] = [d for d in dirs if not d.startswith(".")]
                        for filename in files:
                            ext = os.path.splitext(filename)[1].lower()
                            if ext in IMAGE_EXTENSIONS + VIDEO_EXTENSIONS:
                                full_path = os.path.join(current, filename)
                                try:
                                    modified = os.path.getmtime(full_path)
                                except Exception:
                                    modified = 0
                                kind = "video" if ext in VIDEO_EXTENSIONS else "photo"
                                found.append((modified, {"name": filename, "kind": kind,
                                                        "path": full_path}))
                        if len(found) > 500:
                            break
                except (PermissionError, OSError):
                    continue
            found.sort(key=lambda pair: pair[0], reverse=True)
            items = [item for _, item in found[:60]]
        return items[:60]

    def choose_recent_media(self, item, sheet):
        sheet.dismiss()
        path = item.get("path")
        if not path and item.get("uri") and ANDROID_PICKER_AVAILABLE:
            try:
                Uri = autoclass("android.net.Uri")
                path = self.copy_uri_to_cache(Uri.parse(item["uri"]))
            except Exception as error:
                self.show_message("Could not open media", "Sam Ng could not read this item: " + str(error))
                return
        if path and os.path.isfile(path):
            self.file_selected([path])
        else:
            self.show_message(
                "Could not open media",
                "Sam Ng found this item but could not read it. Check Pydroid's photo and video permissions, then try again."
            )

    def on_android_activity_result(self, request_code, result_code, intent):
        if request_code != self.PICKER_REQUEST_CODE:
            return
        try:
            Activity = autoclass("android.app.Activity")
            if result_code != Activity.RESULT_OK or intent is None:
                return
            uri = intent.getData()
            if uri is None:
                self.show_message("No file selected", "Please tap Create and choose a photo or video.")
                return
            path = self.copy_uri_to_cache(uri, intent)
            if path and os.path.isfile(path):
                Clock.schedule_once(lambda dt, p=path: self.file_selected([p]), 0)
            else:
                Clock.schedule_once(lambda dt: self.show_message(
                    "Could not open this file",
                    "Sam Ng could not copy the selected media into app storage. Try a JPG or MP4 file, or use the built-in file browser."
                ), 0)
        except Exception as error:
            Clock.schedule_once(
                lambda dt, msg=str(error): self.show_message(
                    "Picker error", "Could not import the selected media: " + msg
                ), 0
            )

    def copy_uri_to_cache(self, uri, intent=None):
        """Copy an Android content:// URI to a normal local file for Kivy."""
        try:
            path = self.get_path_from_uri(uri)
            if path and os.path.isfile(path):
                return path
        except Exception:
            pass

        input_stream = None
        buffered_input = None
        output_stream = None
        cursor = None
        try:
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            activity_instance = PythonActivity.mActivity
            resolver = activity_instance.getContentResolver()
            input_stream = resolver.openInputStream(uri)
            if input_stream is None:
                return None

            display_name = "selected_media"
            try:
                OpenableColumns = autoclass("android.provider.OpenableColumns")
                cursor = resolver.query(uri, [OpenableColumns.DISPLAY_NAME], None, None, None)
                if cursor is not None and cursor.moveToFirst():
                    col = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                    if col >= 0:
                        candidate = cursor.getString(col)
                        if candidate:
                            display_name = str(candidate)
            except Exception:
                pass
            finally:
                try:
                    if cursor is not None:
                        cursor.close()
                except Exception:
                    pass

            display_name = display_name.replace("/", "_").replace("\\", "_")
            ext = os.path.splitext(display_name)[1].lower()
            if ext not in IMAGE_EXTENSIONS + VIDEO_EXTENSIONS:
                mime = str(resolver.getType(uri) or "")
                if mime.startswith("image/"):
                    ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}.get(mime, ".jpg")
                elif mime.startswith("video/"):
                    ext = {"video/mp4": ".mp4", "video/webm": ".webm", "video/quicktime": ".mov", "video/3gpp": ".3gp"}.get(mime, ".mp4")
                else:
                    return None

            cache_dir = os.path.join(App.get_running_app().user_data_dir, "selected_media")
            os.makedirs(cache_dir, exist_ok=True)
            destination = os.path.join(cache_dir, "media_" + str(int(Clock.get_time() * 1000)) + ext)

            FileOutputStream = autoclass("java.io.FileOutputStream")
            BufferedInputStream = autoclass("java.io.BufferedInputStream")
            buffered_input = BufferedInputStream(input_stream)
            output_stream = FileOutputStream(destination)
            while True:
                byte_value = buffered_input.read()
                if byte_value == -1:
                    break
                output_stream.write(byte_value)
            output_stream.flush()
            return destination if os.path.isfile(destination) and os.path.getsize(destination) > 0 else None
        except Exception:
            return None
        finally:
            try:
                if buffered_input is not None:
                    buffered_input.close()
                elif input_stream is not None:
                    input_stream.close()
            except Exception:
                pass
            try:
                if output_stream is not None:
                    output_stream.close()
            except Exception:
                pass
            try:
                if cursor is not None:
                    cursor.close()
            except Exception:
                pass

    def get_path_from_uri(self, uri):
        try:
            path = uri.getPath()
            if path and os.path.isfile(path):
                return path
        except Exception:
            pass

        cursor = None
        try:
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            resolver = PythonActivity.mActivity.getContentResolver()
            MediaStore = autoclass("android.provider.MediaStore$MediaColumns")
            cursor = resolver.query(uri, [MediaStore.DATA], None, None, None)
            if cursor is not None and cursor.moveToFirst():
                index = cursor.getColumnIndex(MediaStore.DATA)
                if index >= 0:
                    path = cursor.getString(index)
                    if path and os.path.isfile(path):
                        return path
        except Exception:
            pass
        finally:
            try:
                if cursor is not None:
                    cursor.close()
            except Exception:
                pass
        return None

    def open_fallback_picker(self):
        self.open_recent_media_sheet()

    def use_selection(self, selection, popup):
        popup.dismiss()
        self.file_selected(selection)

    def file_selected(self, selection):
        if not selection:
            self.show_message("No media selected", "Tap Create and choose a photo or video, then confirm the selection.")
            return
        path = selection[0]
        if not isinstance(path, str) or not os.path.isfile(path):
            self.show_message(
                "Cannot open this file",
                "The selected item did not become a readable local file. Please try another photo or video."
            )
            return
        extension = os.path.splitext(path)[1].lower()
        if extension not in IMAGE_EXTENSIONS + VIDEO_EXTENSIONS:
            self.show_message("Unsupported file", "Choose an image or video file.")
            return
        self.selected_path = path
        if path not in self.posts:
            self.posts.append(path)
        self.active_page = "Home"
        self.top_tabs_bar.height = dp(58)
        self.top_tabs_bar.opacity = 1
        self.top_tabs_bar.disabled = False
        for page, button in self.nav_buttons.items():
            button.color = rgba(CYAN if page == "Home" else GREY)
        for tab, button in self.tab_buttons.items():
            button.color = rgba(WHITE if tab == "For You" else GREY)
        self.active_tab = "For You"
        self.show_feed()

    def search(self, *args):
        self.show_message("Search", "search here.")


class SamNgApp(App):
    def build(self):
        Window.clearcolor = rgba(BG)
        manager = ScreenManager(transition=FadeTransition(duration=0.2))
        manager.add_widget(BootScreen(name="boot"))
        manager.add_widget(HomeScreen(name="home"))
        manager.current = "boot"
        return manager


if __name__ == "__main__":
    SamNgApp().run()
