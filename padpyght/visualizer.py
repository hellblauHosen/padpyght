import pygame
#import rpyc

import configurator
import frame_buffer
import images
#import input_history_service

#from multiprocessing import Process


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


def main(skin, joy_index):
    pygame.display.init()
    pygame.joystick.init()

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

    fb = frame_buffer.FrameBuffer(pad_cfg.size, pad_cfg.size,
                                  scale_smooth=pad_cfg.anti_aliasing,
                                  background_color=pad_cfg.background_color)
    pad_gfx = images.PadImage(pad_cfg, fb)

    # Start the input history service process
    #p = Process(target=start_history_process)
    #p.start()

    # Connect to the new process
    #c = rpyc.connect("localhost", 18069)

    # Main input/render loop
    while not pygame.event.peek(pygame.QUIT):
        for event in pygame.event.get():
            if event.type == pygame.JOYBUTTONDOWN:
                if str(event.button) in button_map:
                    elt = button_map[str(event.button)]
                    _get_target(pad_gfx, elt).push(1)
            elif event.type == pygame.JOYBUTTONUP:
                if str(event.button) in button_map:
                    elt = button_map[str(event.button)]
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
                        _get_target(pad_gfx, direction_map['up']).push(y)
                    if 'down' in direction_map:
                        _get_target(pad_gfx, direction_map['down']).push(-y)
                    if 'left' in direction_map:
                        _get_target(pad_gfx, direction_map['left']).push(-x)
                    if 'right' in direction_map:
                        _get_target(pad_gfx, direction_map['right']).push(x)
            fb.handle_event(event)

        pad_gfx.draw()
        fb.flip()
        fb.limit_fps(set_caption=True)


if __name__ == '__main__':
    main('gamecube', 0)


'''
def start_history_process():
    from rpyc.utils.server import ThreadedServer
    from threading import Thread
    import input_history_visualizer

    server = ThreadedServer(input_history_service.InputHistoryService(), port=18069)
    t = Thread(target=server.start)
    t.daemon = True
    t.start()

    input_history_visualizer.main()
'''
