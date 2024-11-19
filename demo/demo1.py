

import graph2LAD
from graph2LAD import Event


events = [Event('INIT','GOTO_HOME','init to home'),
        Event('GOTO_HOME','AT_HOME_POS','Reached home pos'),
        Event('AT_HOME_POS','LOADING','Start loading'),
        Event('LOADING','WORKING','Loading completed'),
        Event('WORKING','UNLOADING','Work complete'),
        Event('UNLOADING','AT_HOME_POS','Unloading complete'),
        Event('INIT','UNLOADING','Direct unloading')]


graph2LAD.render_graph(events,init_state='INIT',fname='demo')
graph2LAD.export_graph(events,'INIT','DemoSchrittKette','demo_FB',45)
