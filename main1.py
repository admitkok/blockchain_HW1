import os
from asyncio import run

from ipv8.community import Community, CommunitySettings
from ipv8.configuration import ConfigBuilder, Strategy, WalkerDefinition, default_bootstrap_defs
from ipv8.lazy_community import lazy_wrapper
from ipv8.messaging.payload_dataclass import dataclass
from ipv8.peerdiscovery.network import PeerObserver
from ipv8.types import Peer
from ipv8.util import run_forever
from ipv8_service import IPv8
import random

@dataclass(msg_id=1)
class Transaction:
    value: int
    to: str

import hashlib
from typing import List

class MerkleNode:
    def __init__(self, value: str) -> None:
        self.value = value
        self.left = None
        self.right = None

    def __repr__(self) -> str:
        return f"MerkleNode({self.value})"

def construct_tree(transactions: List[str]) -> MerkleNode:
    if len(transactions) == 1:
        return MerkleNode(transactions[0])

    # Recursive construction of the tree
    left_child = construct_tree(transactions[:len(transactions) // 2])
    right_child = construct_tree(transactions[len(transactions) // 2:])

    # Combine hashes of left and right children
    combined_hash = hashlib.sha256((left_child.value + right_child.value).encode()).hexdigest()

    # Create parent node
    parent = MerkleNode(combined_hash)
    parent.left = left_child
    parent.right = right_child

    return parent

class MyCommunity(Community, PeerObserver):
    community_id = os.urandom(20)

    def __init__(self, settings: CommunitySettings) -> None:
        super().__init__(settings)
        self.add_message_handler(Transaction, self.on_message)
        self.balances: dict[str, int] = {}
        self.transaction_history: List[str] = []

    def started(self) -> None:
        async def start_communication() -> None:
            try:
                peer = random.choice(self.get_peers())
                if peer:
                    for peer in self.get_peers():
                        self.ez_send(peer, Transaction(10, self.my_peer.public_key.key_to_bin().hex()))
            except:
                pass

        self.register_task("start_communication", start_communication, interval=5.0, delay=0)
        self.network.add_peer_observer(self)

    def on_peer_added(self, peer: Peer) -> None:
        print("I am:", self.my_peer, "I found:", peer)
        self.balances[peer.public_key.key_to_bin().hex()] = 100
        print(
            f"Sent 100 to {peer.public_key.key_to_bin().hex()}. Balance: {self.balances[peer.public_key.key_to_bin().hex()]}")

    def on_peer_removed(self, peer: Peer) -> None:
        pass

    @lazy_wrapper(Transaction)
    def on_message(self, peer: Peer, payload: Transaction) -> None:
        self.balances[peer.public_key.key_to_bin().hex()] = payload.value + self.balances.get(
            peer.public_key.key_to_bin().hex(), 0)
        self.balances[payload.to] = payload.value + self.balances.get(payload.to, 0)
        print(
            f"Received {payload.value} from {peer.public_key.key_to_bin().hex()}. Balance: {self.balances[peer.public_key.key_to_bin().hex()]}")
        print(self.balances)

        # Update transaction history and construct Merkle tree
        self.transaction_history.append(payload.to)
        merkle_tree_root = construct_tree(self.transaction_history)
        print("Merkle Tree Root:", merkle_tree_root.value)

async def start_communities() -> None:
    for i in [1, 2, 3]:
        builder = ConfigBuilder().clear_keys().clear_overlays()
        builder.add_key("my peer", "medium", f"ec{i}.pem")
        builder.add_overlay("MyCommunity", "my peer",
                            [WalkerDefinition(Strategy.RandomWalk,
                                              10, {'timeout': 3.0})],
                            default_bootstrap_defs, {}, [('started',)])
        await IPv8(builder.finalize(),
                   extra_communities={'MyCommunity': MyCommunity}).start()
    await run_forever()

run(start_communities())
