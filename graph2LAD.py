
import xml.etree.ElementTree as ET
from dataclasses import dataclass
import graphviz
import datetime

@dataclass
class Event:
    """
    Represents a transition between two states in a state machine
    """
    src:str
    dest:str
    trigger:str

    def __hash__(self) -> int:
        return hash((self.src,self.dest,self.trigger))



def export_graph(events:list[Event],init_state:str,title:str,fname:str,fb_nr):
    """
    Exports a state machine to a simatic ML file that can be imported to TIA portal
    """
    events = clean_names(events)
    init_state = _clean_str(init_state)

    root = ET.Element("Document") 
    ET.SubElement(root, "Engineering").attrib['version'] = 'V17'
    
    docinfo = ET.SubElement(root, "DocumentInfo")
    ET.SubElement(docinfo, "Created").text = '2021-09-01T12:00:00'
    ET.SubElement(docinfo, "ExportSetting").text = 'None'

    inst_prods = ET.SubElement(docinfo, "InstalledProducts")
    prod = ET.SubElement(inst_prods, "Product")
    ET.SubElement(prod,"DisplayName").text = 'Totally Integrated Automation Portal'
    ET.SubElement(prod,"DisplayVersion").text = 'V17 Update 6'

    uid = UidCounter(0)
    sw = ET.SubElement(root, "SW.Blocks.FB")
    sw.attrib['ID'] = _int2hex(uid.tic())

    attr_list = ET.SubElement(sw, "AttributeList")
    interf = ET.SubElement(attr_list, "Interface")
    sections = ET.SubElement(interf, "Sections")
    sections.attrib['xmlns'] = 'http://www.siemens.com/automation/Openness/SW/Interface/v5'

    inp_section = ET.SubElement(sections, "Section")
    inp_section.attrib['Name'] = 'Input'

    enable_inp = _create_member(inp_section,'enable','Bool')
    _create_multilanguageComment_blk_io(enable_inp,'Enables the state machine')

    reset_inp = _create_member(inp_section,'reset','Bool')
    _create_multilanguageComment_blk_io(reset_inp,'Resets to init state')

    ET.SubElement(sections, "Section").attrib['Name'] = 'Output'
    ET.SubElement(sections, "Section").attrib['Name'] = 'InOut'

    stat_section = ET.SubElement(sections, "Section")
    stat_section.attrib['Name'] = 'Static'

    step0 = _create_member(stat_section,'statStep','Int')
    _create_multilanguageComment_blk_io(step0,'Current step/state')

    step1 = _create_member(stat_section,'statNextStep','Int')
    _create_multilanguageComment_blk_io(step1,'Step/State next PLC cycle')

    ET.SubElement(sections, "Section").attrib['Name'] = 'Temp'
    #triggs = [e.trigger for e in events]
    #for i,t in enumerate(triggs):
    #    _create_member(stat_section,t,'Bool')

    const_section = ET.SubElement(sections, "Section")
    const_section.attrib['Name'] = 'Constant'

    #states = get_states(events)
    states = get_states_sorted(events,init_state)
    for i,s in enumerate(states):
        _create_member(const_section,s,'Int',i*10)

    ET.SubElement(attr_list, "MemoryLayout").text = 'Optimized'
    ET.SubElement(attr_list, "MemoryReserve").text = '100' # TODO, how to calculate this?
    ET.SubElement(attr_list, "Name").text = _clean_str(title)
    ET.SubElement(attr_list, "Number").text = str(fb_nr)
    ET.SubElement(attr_list, "ProgrammingLanguage").text = 'LAD'
    ET.SubElement(attr_list, "SetENOAutomatically").text = 'false'

    obj_list = ET.SubElement(sw, "ObjectList")
    
    # timestamp string : yyyy-mm-dd
    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d")


    blk_comment = "Auto genereted sequence by graph2LAD: " + timestamp_str + '\n'
    blk_comment += 'E.R. https://github.com/eliasrhoden'

    _create_multilingual_text(obj_list,uid,'Comment',blk_comment)

    # Write networks
    _write_reset_net(obj_list,uid,init_state)

    for s in states:

        out_evs = get_outgoing_events(events,s)
        dest_states = [e.dest for e in out_evs]
        if len(dest_states) > 0:
            _write_step_network(obj_list,s,dest_states,uid)

    _write_next_step_net(obj_list,uid)
    _create_multilingual_text(obj_list,uid,'Title',title )

    tree = ET.ElementTree(root)
    ET.indent(tree, space="\t", level=0)
    tree.write(fname + '.xml', encoding='utf-8', xml_declaration=True)


def _int2hex(s):
    """
    Converts an integer to a hex string
    """
    h = hex(s)
    h = h.replace('0x','')
    return h


def get_states(events):
    """
    Returns all states in a state machine
    """
    state_names = set()
    for f in events:
        state_names.add(f.src)
        state_names.add(f.dest)

    return state_names


def get_states_sortedo(events,init_state):
    """
    Sorts states in a state machine, starting from the initial state
    """
    state_names = list()
    state_names.append(init_state)
    
    events_to_check = list()
    current_state = init_state
    history = set()

    while True:

        for e in events:
            if e.src == current_state:
                events_to_check.insert(0,e)
            
        while len(events_to_check)> 0:
            next_event = events_to_check.pop()
            if next_event not in history:
                history.add(next_event)
                if next_event.dest not in state_names:
                    state_names.append(next_event.dest)
                    current_state = next_event.dest
                    break
        
        if len(events_to_check) == 0:
            break 
    return state_names


def get_states_sorted(events,init_state):
    """
    Sorts states in a state machine, starting from the initial state
    """

    states = []
    _dive_states(events,init_state,states)

    return states



def _dive_states(events, current_state, history):
    """
    Recursive function to sort states in a state machine
    """
    history.append(current_state)
    out_evs = get_outgoing_events(events,current_state)
    for e in out_evs:
        if e.dest not in history:
            _dive_states(events,e.dest,history)





def _clean_str(s):
    """
    Cleans state/transitions names for valid TIA variable names
    """
    try:
        a = int(s[0])
        s = '_' + s 
    except:
        pass

    s = s.replace(' ','_')
    s = s.replace('-','_')
    s = s.replace('/','_')
    s = s.replace('\\','_')
    s = s.replace('.','')
    s = s.replace(',','')
    return s.upper()

def clean_names(events):
    """
    Cleans names in events for valid TIA variable names
    """
    for e in events:
        #e.trigger = clean_str(e.trigger)
        e.src = _clean_str(e.src).upper()
        e.dest = _clean_str(e.dest).upper()
    return events

def get_outgoing_events(events:list[Event],current_state)->list[Event]:
    """
    Finds all outgoing events from a state
    """

    out_evs = []

    for e in events: 
        if e.src == current_state:
            out_evs.append(e)

    return out_evs


def _create_member(root, name, datatype,startvalue=None):
    """
    Creates a member element in the XML-file
    Used for FB-interface generation
    """
    member = ET.SubElement(root, "Member")
    member.attrib['Name'] = name
    member.attrib['Datatype'] = datatype

    if startvalue is not None:
        ET.SubElement(member, "StartValue").text = str(startvalue)

    return member


def _add_access_element(root,type,uid,name=''):
    """
    Creates an access element, i.e. reference to a variable in the FB
    Used for LAD-code generation
    """
    access = ET.SubElement(root,"Access")
    access.attrib['UId'] = str(uid)  
    if type == 'stat':
        access.attrib['Scope'] = 'LocalVariable'    
        symb = ET.SubElement(access, "Symbol")
        comp = ET.SubElement(symb, "Component")
        comp.attrib['Name'] = name 
    elif type == 'constant':
        access.attrib['Scope'] = 'LocalConstant'    
        const = ET.SubElement(access, "Constant")
        const.attrib['Name'] = name 
    elif type == 'false':
        access.attrib['Scope'] = 'LiteralConstant'    
        const = ET.SubElement(access, "Constant")
        const_type = ET.SubElement(const, "ConstantType")
        const_type.text = 'Bool'
        const_val = ET.SubElement(const, "ConstantValue")
        const_val.text = 'FALSE'
    else:
        raise ValueError('Unknown type')
    return access, uid

def _add_access_element_scl(root,type,uid,name=''):
    """
    Adds a reference element to a variable in SCL code
    Used for SCL-code generation
    """

    access = ET.SubElement(root,"Access")
    access.attrib['UId'] = str(uid.tic())  
    if type == 'stat':
        access.attrib['Scope'] = 'LocalVariable' 

        symb = ET.SubElement(access, "Symbol")
        symb.attrib['UId'] = str(uid.tic())

        comp = ET.SubElement(symb, "Component")
        comp.attrib['Name'] = name 
        comp.attrib['UId'] = str(uid.tic())

    elif type == 'constant':
        access.attrib['Scope'] = 'LocalConstant'    
        const = ET.SubElement(access, "Constant")
        const.attrib['Name'] = name
        const.attrib['UId'] = str(uid.tic())

    else:
        raise ValueError('Unknown type')
    return access, uid

class UidCounter:
    """
    Counter for UId's in the XML-file
    """
    def __init__(self,init=1):
        self.uid = init

    def tic(self):
        val = self.uid
        self.uid += 1
        return val


def _add_part(root,part,uid):
    """
    Adds a part to a network,
    used for LAD-code generation
    """
    p = ET.SubElement(root,"Part")
    p.attrib['UId'] = str(uid)
    p.attrib['Name'] = part
    if part == 'Eq':
        tv = ET.SubElement(p,"TemplateValue")
        tv.attrib['Name'] = 'SrcType'
        tv.attrib['Type'] = 'Type'
        tv.text = 'Int'
    elif part == 'Contact':
        pass
    elif part == 'Move':
        p.attrib['DisabledENO'] = 'true'
        tv = ET.SubElement(p,"TemplateValue")
        tv.attrib['Name'] = 'Card'
        tv.attrib['Type'] = 'Cardinality'
        tv.text = '1'
    return uid

def _scl_token(root, txt, uid):
    """
    Creates a token-tag for SCL in the XML-file
    Used for SCL-code generation
    """
    tok = ET.SubElement(root,"Token")
    tok.attrib['UId'] = uid
    tok.attrib['Text'] = txt
    return tok

def _write_reset_net(root,net_id, init_state_name):
    """
    Writes the reset network in SCL
    """

    uid = UidCounter(21)
    sw = ET.SubElement(root, "SW.Blocks.CompileUnit")
    sw.attrib['CompositionName'] = 'CompileUnits'
    sw.attrib['ID'] = _int2hex(net_id.tic())
    attr_list = ET.SubElement(sw, "AttributeList")
    net_src = ET.SubElement(attr_list, "NetworkSource")
    st_text = ET.SubElement(net_src,"StructuredText")
    st_text.attrib['xmlns'] = 'http://www.siemens.com/automation/Openness/SW/NetworkSource/StructuredText/v3'
    
    _scl_token(st_text,'IF',str(uid.tic()))
    ET.SubElement(st_text,"Blank").attrib['UId'] = str(uid.tic())
    _add_access_element_scl(st_text,'stat',uid,'reset')
    ET.SubElement(st_text,"Blank").attrib['UId'] = str(uid.tic())
    _scl_token(st_text,'THEN',str(uid.tic()))
    ET.SubElement(st_text,"NewLine").attrib['UId'] = str(uid.tic())

    ET.SubElement(st_text,"Blank").attrib['UId'] = str(uid.tic())
    _add_access_element_scl(st_text,'stat',uid,'statStep')
    ET.SubElement(st_text,"Blank").attrib['UId'] = str(uid.tic())
    _scl_token(st_text,':=',str(uid.tic()))
    ET.SubElement(st_text,"Blank").attrib['UId'] = str(uid.tic())
    _add_access_element_scl(st_text,'constant',uid,init_state_name)
    _scl_token(st_text,';',str(uid.tic()))
    ET.SubElement(st_text,"NewLine").attrib['UId'] = str(uid.tic())

    ET.SubElement(st_text,"Blank").attrib['UId'] = str(uid.tic())
    _add_access_element_scl(st_text,'stat',uid,'statNextStep')
    ET.SubElement(st_text,"Blank").attrib['UId'] = str(uid.tic())
    _scl_token(st_text,':=',str(uid.tic()))
    ET.SubElement(st_text,"Blank").attrib['UId'] = str(uid.tic())
    _add_access_element_scl(st_text,'constant',uid,init_state_name)
    _scl_token(st_text,';',str(uid.tic()))
    ET.SubElement(st_text,"NewLine").attrib['UId'] = str(uid.tic())

    _scl_token(st_text,'END_IF',str(uid.tic()))
    _scl_token(st_text,';',str(uid.tic()))


    ET.SubElement(attr_list,'ProgrammingLanguage').text = 'SCL'

    obj_list = ET.SubElement(sw, "ObjectList")
    _create_multilingual_text(obj_list,net_id,'Title','Reset')


def _write_next_step_net(root,net_id):
    """
    Writes the 'next step' network in SCL
    """

    uid = UidCounter(21)
    sw = ET.SubElement(root, "SW.Blocks.CompileUnit")
    sw.attrib['CompositionName'] = 'CompileUnits'
    sw.attrib['ID'] = _int2hex(net_id.tic())
    attr_list = ET.SubElement(sw, "AttributeList")
    net_src = ET.SubElement(attr_list, "NetworkSource")
    st_text = ET.SubElement(net_src,"StructuredText")
    st_text.attrib['xmlns'] = 'http://www.siemens.com/automation/Openness/SW/NetworkSource/StructuredText/v3'

    _scl_token(st_text,'IF',str(uid.tic()))
    ET.SubElement(st_text,"Blank").attrib['UId'] = str(uid.tic())
    _add_access_element_scl(st_text,'stat',uid,'enable')
    ET.SubElement(st_text,"Blank").attrib['UId'] = str(uid.tic())
    _scl_token(st_text,'THEN',str(uid.tic()))
    ET.SubElement(st_text,"NewLine").attrib['UId'] = str(uid.tic())

    ET.SubElement(st_text,"Blank").attrib['UId'] = str(uid.tic())
    _add_access_element_scl(st_text,'stat',uid,'statStep')
    ET.SubElement(st_text,"Blank").attrib['UId'] = str(uid.tic())
    _scl_token(st_text,':=',str(uid.tic()))
    ET.SubElement(st_text,"Blank").attrib['UId'] = str(uid.tic())
    _add_access_element_scl(st_text,'stat',uid,'statNextStep')
    _scl_token(st_text,';',str(uid.tic()))
    ET.SubElement(st_text,"NewLine").attrib['UId'] = str(uid.tic())

    _scl_token(st_text,'END_IF',str(uid.tic()))
    _scl_token(st_text,';',str(uid.tic()))


    ET.SubElement(attr_list,'ProgrammingLanguage').text = 'SCL'

    obj_list = ET.SubElement(sw, "ObjectList")
    _create_multilingual_text(obj_list,net_id,'Title','Next step')
    _create_multilingual_text(obj_list,net_id,'Comment','This ensurers that we remain in each state step at least 1 plc cycle')




def _write_step_network(root,src_step, dest_steps,uid_counter):
    """
    Writes a network for a step in the state machine
    It contains a single src_step and multiple dest_steps
    """

    uid = UidCounter(21)
    sw = ET.SubElement(root, "SW.Blocks.CompileUnit")

    sw.attrib['CompositionName'] = 'CompileUnits'
    sw.attrib['ID'] = _int2hex(uid_counter.tic())
    attr_list = ET.SubElement(sw, "AttributeList")
    net_src = ET.SubElement(attr_list, "NetworkSource")
    FlgNet = ET.SubElement(net_src,"FlgNet")
    FlgNet.attrib['xmlns'] = 'http://www.siemens.com/automation/Openness/SW/NetworkSource/FlgNet/v4'
    parts = ET.SubElement(FlgNet,"Parts")

    _,statUid=_add_access_element(parts,'stat',uid.tic(),'statStep')
    _,src_step_uid=_add_access_element(parts,'constant',uid.tic(),src_step)

    
    statNextStepUids = []
    false_uids = []
    for _ in range(len(dest_steps)):
        _,falseUid=_add_access_element(parts,'false',uid.tic())
        false_uids.append(falseUid)

        _,statNextUid = _add_access_element(parts,'stat',uid.tic(),'statNextStep')
        statNextStepUids.append(statNextUid)

    dest_uids = []

    for d in dest_steps:
        dest_uid = uid.tic()
        dest_uids.append(dest_uid)
        _add_access_element(parts,'constant',dest_uid,d)

    eqUid = _add_part(parts,'Eq',uid.tic())

    contactUids = []
    moveUids = []

    for d in dest_uids:
        contactUid = uid.tic()
        contactUids.append(contactUid)
        _add_part(parts,'Contact',contactUid)
        moveUid = uid.tic()
        moveUids.append(moveUid)
        _add_part(parts,'Move',moveUid)

    wires = ET.SubElement(FlgNet,"Wires")

    # power rail to EQ-pre
    wire = ET.SubElement(wires,"Wire")
    wire.attrib['UId'] = str(uid.tic())
    ET.SubElement(wire,"Powerrail")
    nc = ET.SubElement(wire,"NameCon")
    nc.attrib['UId'] = str(eqUid)
    nc.attrib['Name'] = 'pre'

    # statStep to EQ-in1
    wire = ET.SubElement(wires,"Wire")
    wire.attrib['UId'] = str(uid.tic())

    ic = ET.SubElement(wire,"IdentCon")
    ic.attrib['UId'] = str(statUid)

    nc = ET.SubElement(wire,"NameCon")
    nc.attrib['UId'] = str(eqUid)
    nc.attrib['Name'] = 'in1'

    # src_step to EQ-in2
    wire = ET.SubElement(wires,"Wire")
    wire.attrib['UId'] = str(uid.tic())

    ic = ET.SubElement(wire,"IdentCon")
    ic.attrib['UId'] = str(src_step_uid)

    nc = ET.SubElement(wire,"NameCon")
    nc.attrib['UId'] = str(eqUid)
    nc.attrib['Name'] = 'in2'

    # EQ-out to contacts
    wire = ET.SubElement(wires,"Wire")
    wire.attrib['UId'] = str(uid.tic())
    
    nc = ET.SubElement(wire,"NameCon")
    nc.attrib['UId'] = str(eqUid)   
    nc.attrib['Name'] = 'out'

    for c in contactUids:
        nc = ET.SubElement(wire,"NameCon")
        nc.attrib['UId'] = str(c)
        nc.attrib['Name'] = 'in'

    # connect constants to contacts and moves
    for c,m,dest,false_uid,statNxtStep in zip(contactUids,moveUids,dest_uids,false_uids,statNextStepUids):
        # contact
        wire = ET.SubElement(wires,"Wire")
        wire.attrib['UId'] = str(uid.tic())

        ic = ET.SubElement(wire,"IdentCon")
        ic.attrib['UId'] = str(false_uid)

        nc = ET.SubElement(wire,"NameCon")
        nc.attrib['UId'] = str(c)
        nc.attrib['Name'] = 'operand'

        # contact -> move
        wire = ET.SubElement(wires,"Wire")
        wire.attrib['UId'] = str(uid.tic())

        nc1 = ET.SubElement(wire,"NameCon")
        nc1.attrib['UId'] = str(c)
        nc1.attrib['Name'] = 'out'

        nc2 = ET.SubElement(wire,"NameCon")
        nc2.attrib['UId'] = str(m)
        nc2.attrib['Name'] = 'en'
        
        # move in1
        wire = ET.SubElement(wires,"Wire")
        wire.attrib['UId'] = str(uid.tic())
        ic = ET.SubElement(wire,"IdentCon")
        ic.attrib['UId'] = str(dest)
        nc = ET.SubElement(wire,"NameCon")
        nc.attrib['UId'] = str(m)
        nc.attrib['Name'] = 'in'

        # connect moves to statNextStep
        wire = ET.SubElement(wires,"Wire")
        wire.attrib['UId'] = str(uid.tic())
        nc = ET.SubElement(wire,"NameCon")
        nc.attrib['UId'] = str(m)
        nc.attrib['Name'] = 'out1'
        ic = ET.SubElement(wire,"IdentCon")
        ic.attrib['UId'] = str(statNxtStep)

    ET.SubElement(attr_list,'ProgrammingLanguage').text = 'LAD'

    obj_list = ET.SubElement(sw, "ObjectList")

    comment_str = src_step + '\n'
    for d in dest_steps:
        comment_str += '\t -> ' + str(d) + ' \n'

    _create_multilingual_text(obj_list,uid_counter,'Comment',comment_str)
    _create_multilingual_text(obj_list,uid_counter,'Title',src_step)

    return sw

def _create_multilingual_text(root,id_counter,type,text):
    """
    Creates multilingual text elements for each language
    for network titles and comments
    """

    mlt = ET.SubElement(root,"MultilingualText")
    mlt.attrib['ID'] = _int2hex(id_counter.tic())
    mlt.attrib['CompositionName'] = type

    obj_list = ET.SubElement(mlt, "ObjectList")

    cultures = ['sv-SE','de-DE','en-US','es-ES','fr-FR','it-IT','ja-JP','zh-CN']

    for c in cultures:
        mlt_item = ET.SubElement(obj_list, "MultilingualTextItem")
        mlt_item.attrib['ID'] = _int2hex(id_counter.tic())
        mlt_item.attrib['CompositionName'] = 'Items'

        attr_list = ET.SubElement(mlt_item, "AttributeList")
        cult = ET.SubElement(attr_list, "Culture")
        cult.text = c
        text_elem = ET.SubElement(attr_list, "Text")
        text_elem.text = text

def _create_multilanguageComment_blk_io(root,text):
    """
    Adds comment to a block i/o signal
    """

    comment = ET.SubElement(root,"Comment")

    cultures = ['sv-SE','de-DE','en-US','es-ES','fr-FR','it-IT','ja-JP','zh-CN']

    for c in cultures:
        mlt = ET.SubElement(comment,"MultiLanguageText")
        mlt.attrib['Lang'] = c
        mlt.text = text


def render_graph(events:list[Event],init_state:str,fname:str,clean_event_names=True):
    """
    Renders a graph of the state machine to a pdf file
    """

    if clean_event_names:
        events = clean_names(events)
        init_state = _clean_str(init_state)
    f = graphviz.Digraph('finite_state_machine', filename=fname,format='pdf')
    # LR = Horizontal, TB = Vertical
    f.attr(rankdir='TB')

    f.attr('node', shape='doublecircle')
    f.node(init_state)

    #f.attr('node', shape='circle')
    f.attr('node',shape='')
    for e in events:
        f.edge(e.src, e.dest, label=e.trigger)

    f.view()


