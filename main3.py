import os
from asyncio import run

from ipv8.community import Community, CommunitySettings
from ipv8.configuration import ConfigBuilder, Strategy, WalkerDefinition, default_bootstrap_defs
from ipv8.lazy_community import lazy_wrapper
from ipv8.messaging.payload_dataclass import dataclass
from ipv8.types import Peer
from ipv8.util import run_forever
from ipv8_service import IPv8
from ipv8.peerdiscovery.network import PeerObserver
from hashlib import sha256

# Find a nonce such that the hash of "Dima"+nonce starts with six zeros
def find_nonce():
    nonce = 0
    while True:
        input_str = "Alex" + str(nonce)
        hash_result = sha256(input_str.encode()).hexdigest()
        if hash_result.startswith('0'):
            return nonce, hash_result
        nonce += 1


@dataclass(msg_id=1)
class PuzzleMessage:
    name: str
    nonce: int
    amount: int

@dataclass(msg_id=2)
class Transaction:
    value: int
    to: str


class MyCommunity(Community, PeerObserver):
    community_id = b'blockchainbytem23332'

    def on_peer_added(self, peer: Peer) -> None:
        print("I am:", self.my_peer, "I found:", peer)

    def on_peer_removed(self, peer: Peer) -> None:
        pass

    def started(self) -> None:
        self.network.add_peer_observer(self)

        async def start_communication() -> None:
            for p in self.get_peers():
                nonce, hash_result = find_nonce()
                print(nonce, hash_result)
                amount = int(input("Enter amount: "))
                self.ez_send(p, PuzzleMessage(name="Alex", nonce=6, amount= amount))
                self.ez_send(p, Transaction(value=amount, to="Dima"))

        self.register_task("start_communication", start_communication, interval=5.0, delay=0)

    @lazy_wrapper(PuzzleMessage)
    def on_message(self, peer: Peer, payload: PuzzleMessage) -> None:
        print(f"Received a message from {peer} with name {payload.name} and puzzle {payload.nonce},\n amount: {payload.amount}")


async def start_communities() -> None:
    for i in range(3):
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