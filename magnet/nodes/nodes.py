# coding=utf-8
import torch
import magnet as mag

from torch import nn

from magnet.utils.misc import caller_locals

class Node(nn.Module):
    r"""Abstract base class that defines MagNet's Node implementation.

        A Node is a *'self-aware Module'*.
        It can dynamically parametrize itself in runtime.

        For instance, a ``Linear`` Node can infer the input features
        automatically when first called; a ``Conv`` Node can infer the
        dimensionality (1, 2, 3) of the input automatically.

        MagNet's Nodes strive to help the developer as much as possible by
        finding the right hyperparameter values automatically.
        Ideally, the developer shouldn't need to define anything
        except the basic architecture and the inputs and outputs.

        The arguments passed to the constructor are stored in a ``_args``
        attribute as a dictionary.

        This is later modified by the :py:meth:`build` method which gets
        automatically called on the first forward pass.

        Keyword Args:
            name (str) - A printable name for this node. Default: Class Name
        """

    def __init__(self, *args, **kwargs):
        super().__init__()
        self._parse_args()
        self._built = False

    def build(self, *args, **kwargs):
        r"""Builds the Node.
        Ideally, should not be called manually.

        When an unbuilt module is first called, this method gets invoked.
        """
        self._built = True
        self.to(mag.device)

    def __call__(self, *args, **kwargs):
        if not (self._built and mag.build_lock): self.build(*args, **kwargs)
        return super().__call__(*args, **kwargs)

    def _parse_args(self):
        """ A Helper Method to get all the constructor arguments
        and store them into _args.

        This will help modify these arguments at runtime.

        Additionally, this method also captures the name of the
        Node, if given (default is the class name).
        """
        args = caller_locals(ancestor=True)
        args.update(args.pop('kwargs', {}))

        self.name = args.pop('name', self.__class__.__name__)

        if self.name is None or self.name == '':
            raise ValueError(f"""One of the {self.__class__.__name__} Node's
                             names is {self.name}""")

        self._args = args

    def get_args(self):
        """ Returns a nicely formatted string describing the argumens
        """
        return ', '.join(str(k) + '=' + str(v) for k, v in self._args.items())

    def to(self, *args, **kwargs):
        super().to(*args, **kwargs)

        # Additionally, set a convinient device attribute

        try: self.device = next(self.parameters())[0].device
        except StopIteration: pass

        return self

    def load_state_dict(self, f):
        from pathlib import Path

        # Handle a path being given instead of a file. (preferred since it
        # automatically maps to the correct device)
        if isinstance(f, (str, Path)):
            device = self.device.type
            if device == 'cuda': device = 'cuda:0'

            return super().load_state_dict(torch.load(f, map_location=device))
        else:
            return super().load_state_dict(f)

    def  _mul_int(self, n):
        return [self] + [self.__class__(**self._args) for _ in range(n - 1)]

    def  _mul_list(self, n):
        r"""A useful overload of the * operator that can create similar
        copies of the node.

        Args:
            n (tuple or list) - The modifier supplied

        The modifier n should be used to change the arguments of the
        node in a meaningful way.

        For instance, in the case of a Linear node, the items in n
        can be interpreted as the output dimensions of each layer.
        """
        raise NotImplementedError

    def __mul__(self, n):
        if isinstance(n, int) or (isinstance(n, float) and n.is_integer()):
            return self._mul_int(n)

        if isinstance(n, (tuple, list)):
            return self._mul_list(n)
