import copy
import pygame

from multiprocessing import Process

import configurator
import frame_buffer
import images


class InputState:
    """
    Represents a comparable state of all inputs.
    Also tracks the number of frames that this state has been current.
    """

    def __init__(self):
        self.button_map = dict()  # button name to value
        self.axis_map = dict()  # axis name/index to value
        # TODO: joystick
        self.elapsed_frames = 0

    def __eq__(self, other):
        if not isinstance(other, InputState):
            return False
        return self.button_map == other.button_map and self.axis_map == other.axis_map

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self.button_map, self.axis_map)

    def __str__(self):
        return str(self.button_map) + str(self.axis_map)


def start_history_process(skin, joy_index):
    """
    Method passed to a new Process to start this class in input history mode.
    :param skin: See the documentation for main
    :param joy_index: See the documentation for main
    :return: None
    """
    main(skin, joy_index, False)


def _get_target(pad_gfx, map_element):
    elt_type = map_element['type']
    elt_name = map_element['name']
    target = None
    if elt_type == 'button':
        target = pad_gfx.buttons[elt_name]
    elif elt_type == 'trigger':
        target = pad_gfx.triggers[elt_name]
    elif elt_type == 'stick':
        which = map_element['direction']
        target = pad_gfx.sticks[elt_name].directions[which]
    assert target is not None
    return target


def main(skin, joy_index,  is_main_process):
    pygame.display.init()
    pygame.joystick.init()
    pygame.font.init()

    joy = pygame.joystick.Joystick(joy_index)
    joy.init()
    mappings = configurator.load_mappings(skin)
    if joy.get_name() not in mappings:
        print 'Please run the mapper on', joy.get_name(), 'with', skin, 'skin.'
        return

    mappings = mappings[joy.get_name()]

    button_map = mappings.get('button', dict())
    axis_map = mappings.get('axis', dict())
    hat_map = mappings.get('hat', dict())

    pad_cfg = configurator.PadConfig(skin)

    height = pad_cfg.size[1]
    size = pad_cfg.size if is_main_process else (pad_cfg.size[0], height * 10)
    fb = frame_buffer.FrameBuffer(size, size,
                                  scale_smooth=pad_cfg.anti_aliasing,
                                  background_color=pad_cfg.background_color)
    pad_gfx = images.PadImage(pad_cfg, fb)

    timer_font = pygame.font.SysFont(None, 16)

    # Start the input history service process
    if is_main_process:
        p = Process(target=start_history_process, args=(skin, joy_index))
        p.start()

    # TODO: May want to initialize all inputs
    last_state = InputState()

    # Main input/render loop
    while not pygame.event.peek(pygame.QUIT):

        new_state = copy.deepcopy(last_state)

        for event in pygame.event.get():
            if event.type == pygame.JOYBUTTONDOWN:
                if str(event.button) in button_map:
                    elt = button_map[str(event.button)]
                    new_state.button_map[elt['name']] = 1
                    _get_target(pad_gfx, elt).push(1)
            elif event.type == pygame.JOYBUTTONUP:
                if str(event.button) in button_map:
                    elt = button_map[str(event.button)]
                    new_state.button_map[elt['name']] = 0
                    _get_target(pad_gfx, elt).push(0)
            elif event.type == pygame.JOYAXISMOTION:
                if str(event.axis) in axis_map:
                    for change, elt in axis_map[str(event.axis)].iteritems():
                        change = int(change)
                        value = event.value
                        if abs(change) == 2:
                            value += change / abs(change)
                        value /= change
                        value = max(0, value)
                        _get_target(pad_gfx, elt).push(value)
            elif event.type == pygame.JOYHATMOTION:
                if str(event.hat) in hat_map:
                    direction_map = hat_map[str(event.hat)]
                    x, y = event.value
                    if 'up' in direction_map:
                        new_state.button_map[direction_map['up']['name']] = y
                        _get_target(pad_gfx, direction_map['up']).push(y)
                    if 'down' in direction_map:
                        new_state.button_map[direction_map['down']['name']] = -y
                        _get_target(pad_gfx, direction_map['down']).push(-y)
                    if 'left' in direction_map:
                        new_state.button_map[direction_map['left']['name']] = -x
                        _get_target(pad_gfx, direction_map['left']).push(-x)
                    if 'right' in direction_map:
                        new_state.button_map[direction_map['right']['name']] = x
                        _get_target(pad_gfx, direction_map['right']).push(x)
            fb.handle_event(event)

        if is_main_process:
            pad_gfx.draw()
            fb.flip()
        else:
            if last_state != new_state:
                new_state.elapsed_frames = 0
                print("L: " + str(last_state) + ", N:" + str(new_state))
                fb.scroll(0, height)
                pad_gfx.draw()
                fb.flip()
            else:
                new_state.elapsed_frames += 1  # TODO: Actual frames
                font_image = timer_font.render(
                    str(new_state.elapsed_frames),
                    True,
                    pygame.Color(255, 255, 255),
                    pad_cfg.background_color)
                fb.blit(font_image, (0, 0))
            last_state = new_state

        fb.limit_fps(set_caption=True)


if __name__ == '__main__':
    main('gamecube', 0, True)
