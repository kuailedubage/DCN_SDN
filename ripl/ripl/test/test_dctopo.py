#!/usr/bin/env python
'''Test network creation.

@author Brandon Heller (brandonh@stanford.edu)
'''

import unittest

from ripl.dctopo import FatTreeTopo, BCubeTopo


class testFatTreeTopo(unittest.TestCase):
    '''Test FatTreeTopo with varying k,r.'''

    @staticmethod
    def testCreateTopos():
        '''Create multiple topos.'''
        sizes = xrange(4, 32, 2)
        for k in sizes:
            ratios = xrange(1, k/2+1)
            for r in ratios:
                if k//2 % r == 0:
                    FatTreeTopo(k, r)

    def testValidateTopos(self):
        '''Verify number of hosts, switches, and nodes at each layer.'''
        sizes = xrange(4, 32, 2)
        for k in sizes:
            ratios = xrange(1, k/2+1)
            for r in ratios:
                if k//2 % r == 0:
                    ft = FatTreeTopo(k, r)

                    hosts = (k ** 3) / 4
                    self.assertEqual(len(ft.hosts()), hosts)
                    switches = 4 * ((k ** 2) / 4) + ((k ** 2) / 4)/r
                    self.assertEqual(len(ft.switches()), switches)
                    nodes = hosts + switches
                    self.assertEqual(len(ft.nodes()), nodes)
                    self.assertEqual(len(ft.layer_nodes(0)), ((k ** 2) / 4) / r)
                    self.assertEqual(len(ft.layer_nodes(1)), (k ** 2) / 2)
                    self.assertEqual(len(ft.layer_nodes(2)), (k ** 2) / 2)
                    self.assertEqual(len(ft.layer_nodes(3)), (k ** 3) / 4)
                    self.assertEqual(len(ft.links()), k**3 / (4 * r) + k ** 3 / 2)
                    for sw in ft.layer_nodes(1):
                        self.assertEqual(len(ft.up_nodes(sw)), k/(2 * r))

    # def testLinksPerNode(self):
    #     sizes = xrange(4, 16, 2)
    #     for k in sizes:
    #         ratios = xrange(1, k/2+1)
    #         for r in ratios:
    #             if k//2 % r == 0:
    #                 ft = FatTreeTopo(k, r)
    #                 for n in ft.layer_nodes(3):
    #                     self.assertEqual(len(ft.s()), switches)

    # def testNodeID(self):
    #     '''Verify NodeID conversion in both directions.'''
    #     pairs = {(0, 0, 1): 0x000001,
    #              (0, 1, 1): 0x000101,
    #              (1, 0, 1): 0x010001}
    #     for a, b in pairs.iteritems():
    #         (x, y, z) = a
    #         self.assertEqual(FatTreeTopo.FatTreeNodeID(x, y, z).dpid, b)
    #         self.assertEqual(str(FatTreeTopo.FatTreeNodeID(dpid = b)), str(a))
    #
    # def testUpNodesAndEdges(self):
    #     '''Verify number of up edges at each layer.'''
    #     ft = FatTreeTopo(4)
    #
    #     # map FatTreeNodeID inputs to down node/edge totals
    #     pairs = {(0, 0, 2): 1,
    #              (0, 0, 1): 2,
    #              (0, 2, 1): 2}
    #     for a, b in pairs.iteritems():
    #         (x, y, z) = a
    #         host = FatTreeTopo.FatTreeNodeID(x, y, z).name_str()
    #         self.assertEqual(len(ft.up_nodes(host)), b)
    #         self.assertEqual(len(ft.up_edges(host)), b)
    #
    # def testDownNodesAndEdges(self):
    #     '''Verify number of down edges at each layer.'''
    #     ft = FatTreeTopo(4)
    #
    #     # map FatTreeNodeID inputs to down node/edge totals
    #     pairs = {(0, 0, 1): 2,
    #              (0, 2, 1): 2,
    #              (4, 1, 1): 4}
    #     for a, b in pairs.iteritems():
    #         (x, y, z) = a
    #         host = FatTreeTopo.FatTreeNodeID(x, y, z).name_str()
    #         self.assertEqual(len(ft.down_nodes(host)), b)
    #         self.assertEqual(len(ft.down_edges(host)), b)
    #
    # def testPorts(self):
    #     '''Verify port numbering between selected nodes.'''
    #     ft = FatTreeTopo(4)
    #
    #     tuples = [((0, 0, 2), (0, 0, 1), 0, 2),
    #               ((0, 0, 1), (0, 2, 1), 1, 2),
    #               ((0, 0, 1), (0, 3, 1), 3, 2),
    #               ((0, 2, 1), (4, 1, 1), 1, 1),
    #               ((0, 2, 1), (4, 1, 2), 3, 1),
    #               ((3, 3, 1), (4, 2, 1), 1, 4)
    #               ]
    #     for tuple_ in tuples:
    #         src, dst, srcp_exp, dstp_exp = tuple_
    #         x, y, z = src
    #         x2, y2, z2 = dst
    #         src_dpid = FatTreeTopo.FatTreeNodeID(x, y, z).name_str()
    #         dst_dpid = FatTreeTopo.FatTreeNodeID(x2, y2, z2).name_str()
    #         (srcp, dstp) = ft.port(src_dpid, dst_dpid)
    #         self.assertEqual(srcp, srcp_exp)
    #         self.assertEqual(dstp, dstp_exp)
    #         # flip order and ensure same result
    #         (dstp, srcp) = ft.port(dst_dpid, src_dpid)
    #         self.assertEqual(srcp, srcp_exp)
    #         self.assertEqual(dstp, dstp_exp)
    #


class testBCubeTopo(unittest.TestCase):
    '''Test BCubeTopo with varying k,n.'''

    @staticmethod
    def testCreateTopos():
        '''Create multiple topos.'''
        levels = xrange(0, 4)
        for k in levels:
            num = xrange(1, 5)
            for n in num:
                BCubeTopo(k, n)

    def testValidateTopos(self):
        '''Verify number of hosts, switches, and nodes at each layer.'''
        levels = xrange(0, 4)
        for k in levels:
            num = xrange(1, 5)
            for n in num:
                bc = BCubeTopo(k, n)

                hosts = n ** (k + 1)
                self.assertEqual(len(bc.hosts()), hosts)
                switches = (k + 1) * (n ** k)
                self.assertEqual(len(bc.switches()), switches)
                nodes = hosts + switches
                self.assertEqual(len(bc.nodes()), nodes)
                self.assertEqual(len(bc.layer_nodes(-1)), hosts)
                for i in xrange(k + 1):
                    self.assertEqual(len(bc.layer_nodes(i)), n ** k)
                self.assertEqual(len(bc.links()), switches * n)

    def testLinksPerNode(self):
        '''test links between nodes'''
        levels = xrange(0, 4)
        for k in levels:
            num = xrange(1, 5)
            for n in num:
                bc = BCubeTopo(k, n)
                for h in bc.hosts():
                    self.assertEqual(len(bc.g[h]), k + 1)
                for s in bc.switches():
                    self.assertEqual(len(bc.g[s]), n)

if __name__ == '__main__':
    # unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(testBCubeTopo)
    unittest.TextTestRunner(verbosity=2).run(suite)