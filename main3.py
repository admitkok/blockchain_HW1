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


@dataclass(msg_id=1)
class PuzzleMessage:
    name: str
    nonce: int


class MyCommunity(Community, PeerObserver):
    community_id = b'harbourspaceuniverse'

    def on_peer_added(self, peer: Peer) -> None:
        print("I am:", self.my_peer, "I found:", peer)

    def on_peer_removed(self, peer: Peer) -> None:
        pass

    def started(self) -> None:
        self.network.add_peer_observer(self)

        async def start_communication() -> None:
            for p in self.get_peers():
                self.ez_send(p, PuzzleMessage(name="Alex", nonce=46367806))

        self.register_task("start_communication", start_communication, interval=5.0, delay=0)

    @lazy_wrapper(PuzzleMessage)
    def on_message(self, peer: Peer, payload: PuzzleMessage) -> None:
        print(f"Received a message from {peer} with name {payload.name} and puzzle {payload.puzzle}")


async def start_communities() -> None:
    for i in range(1):
        builder = ConfigBuilder().clear_keys().clear_overlays()
        builder.add_key("my peer", "medium", f"ec{i}.pem")
        # We provide the 'started' function to the 'on_start'.
        # We will call the overlay's 'started' function without any
        # arguments once IPv8 is initialized.
        builder.add_overlay("MyCommunity", "my peer",
                            [WalkerDefinition(Strategy.RandomWalk,
                                              10, {'timeout': 3.0})],
                            default_bootstrap_defs, {}, [('started',)])
        await IPv8(builder.finalize(),
                   extra_communities={'MyCommunity': MyCommunity}).start()
    await run_forever()


run(start_communities())