from base import INodeInfo
from options_dict import OptionsDict


class UnitNodeInfo(INodeInfo):
    """
    Throwaway NodeInfo implementation for unit testing purposes.
    """
    def __init__(self, name):
        self.name = name
    
    def belongs_to_any(self, collection_names):
        return False
        
    def str(self, absolute=None, relative=None, collection_separator=None,
            only_indent=False):
        return self.name


class UnitOptionsDict(OptionsDict):
    """
    This is OptionsDict decoupled from the NodeInfo and NodeFormat
    implementations for unit testing purposes.
    """
    def create_orphan_node_info(self, node_name):
        return UnitNodeInfo(node_name)

    def create_array_node_info(self, array_name, node_names, node_index):
        return UnitNodeInfo(':'.join((array_name, node_names[node_index])))

    def create_node_info_formatter(self, which=None):
        return lambda node_info, absolute, relative: ''
        
    # def str(self, absolute=None, relative=None, collection_separator=None):
    #     return dict.__str__(self)
