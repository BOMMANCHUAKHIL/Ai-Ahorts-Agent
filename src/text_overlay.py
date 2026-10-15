def make_title_clip(text, width):
    return TextClip(text, fontsize=70, color="white",
                    stroke_color="black", stroke_width=3
                    ).set_position(("center", 300)).set_duration(3)

def make_fact_clip(text, width):
    return TextClip(f"💡 {text}", fontsize=55, color="yellow",
                    ).set_position(("center", 1200)).set_duration(4).set_start(7)

def make_cta_clip():
    return TextClip("Follow for more!", fontsize=60, color="white"
                    ).set_position(("center", 1600)).set_duration(4).set_start(11)