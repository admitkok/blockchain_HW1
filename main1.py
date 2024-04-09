import os
from asyncio import run

from ipv8.community import Community, CommunitySettings
from ipv8.configuration import ConfigBuilder, Strategy, WalkerDefinition, default_bootstrap_defs
from ipv8.lazy_community import lazy_wrapper
from ipv8.messaging.payload_dataclass import dataclass
from ipv8.types import Peer
from ipv8.util import run_forever
from ipv8_service import IPv8


@dataclass(msg_id=1)
class MyMessage:
    clock: int


@dataclass(msg_id=2)  # Define a new message class for transactions
class Transaction:
    amount: int


class MyCommunity(Community):
    community_id = os.urandom(20)

    def __init__(self, settings: CommunitySettings) -> None:
        super().__init__(settings)
        self.add_message_handler(MyMessage, self.on_message)
        self.add_message_handler(Transaction, self.on_transaction)  # Add message handler for transactions
        self.lamport_clock = 0
        self.balance = 1000  # Initialize balance for each peer

    def started(self) -> None:
        async def start_communication() -> None:
            if not self.lamport_clock:
                for p in self.get_peers():
                    self.ez_send(p, MyMessage(self.lamport_clock))
            else:
                self.cancel_pending_task("start_communication")

        self.register_task("start_communication", start_communication, interval=5.0, delay=0)

    @lazy_wrapper(MyMessage)
    def on_message(self, peer: Peer, payload: MyMessage) -> None:
        self.lamport_clock = max(self.lamport_clock, payload.clock) + 1
        print(self.my_peer, "current clock:", self.lamport_clock)
        self.ez_send(peer, MyMessage(self.lamport_clock))

    @lazy_wrapper(Transaction)
    def on_transaction(self, peer: Peer, payload: Transaction) -> None:
        # Update local balance based on the transaction
        self.balance += payload.amount
        print(f"Peer {self.my_peer} updated balance: {self.balance}")

        # Broadcast the transaction to other peers
        for p in self.get_peers():
            if p != peer:  # Avoid sending the transaction back to the sender
                self.ez_send(p, Transaction(payload.amount))


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
