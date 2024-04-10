import os
import asyncio

from ipv8.community import Community, CommunitySettings
from ipv8.configuration import ConfigBuilder, Strategy, WalkerDefinition, default_bootstrap_defs
from ipv8.lazy_community import lazy_wrapper
from ipv8.messaging.payload import Payload
from ipv8.messaging.payload_dataclass import dataclass
from ipv8.types import Peer
from ipv8.util import run_forever
from ipv8_service import IPv8


@dataclass(msg_id=1)
class MyMessage:
    clock: int


@dataclass(msg_id=2)
class Transaction(Payload):

    def __init__(self, amount):
        self.amount = amount

    def from_bytes(self, data):
        self.amount = int.from_bytes(data, byteorder='big')

    def to_bytes(self):
        return self.amount.to_bytes(8, byteorder='big')


class MyCommunity(Community):
    community_id = os.urandom(20)
    community_instance = None

    def __init__(self, settings: CommunitySettings) -> None:
        super().__init__(settings)
        self.add_message_handler(MyMessage, self.on_message)
        self.add_message_handler(Transaction, self.on_transaction)
        self.lamport_clock = 0
        self.balance = 1000

    def started(self) -> None:
        async def start_communication() -> None:
            if not self.lamport_clock:
                for p in self.get_peers():
                    self.ez_send(p, MyMessage(self.lamport_clock))
            else:
                self.cancel_pending_task("start_communication")

        self.register_task("start_communication", start_communication, interval=5.0, delay=0)

    @classmethod
    async def create_community(cls) -> 'MyCommunity':
        if cls.community_instance is None:
            builder = ConfigBuilder().clear_keys().clear_overlays()
            builder.add_key("my peer", "medium", "ec.pem")
            builder.add_overlay("MyCommunity", "my peer",
                                [WalkerDefinition(Strategy.RandomWalk,
                                                  10, {'timeout': 3.0})],
                                default_bootstrap_defs, {}, [('started',)])
            cls.community_instance = await IPv8(builder.finalize(),
                                                extra_communities={'MyCommunity': cls}).start()
        return cls.community_instance
        await run_forever()

    @lazy_wrapper(MyMessage)
    def on_message(self, peer: Peer, payload: MyMessage) -> None:
        self.lamport_clock = max(self.lamport_clock, payload.clock) + 1
        print(self.my_peer, "current clock:", self.lamport_clock)
        self.ez_send(peer, MyMessage(self.lamport_clock))

    @lazy_wrapper(Transaction)
    def on_transaction(self, peer: Peer, payload: Transaction) -> None:
        self.balance += payload.amount
        print(f"Peer {self.my_peer} updated balance: {self.balance}")
        for p in self.get_peers():
            if p != peer:
                self.ez_send(p, Transaction(payload.amount))


async def send_transaction():
    community = await MyCommunity.create_community()
    if community is not None:
        peers = community.get_peers()
        if len(peers) >= 2:
            peer_2 = peers[1]
            amount = 100
            transaction = Transaction(amount)
            community.ez_send(peer_2, transaction)
            print(f"Transaction sent from Peer 1 to Peer 2: Amount {amount}")
    else:
        print("Community object is None. Unable to send transaction.")


async def key_listener():
    while True:
        key = await asyncio.get_event_loop().run_in_executor(None, input, "Press 'g' to send a transaction, 'q' to quit: ")
        if key.strip() == 'g':
            asyncio.create_task(send_transaction())
        elif key.strip() == 'q':
            break


async def main():
    community = await MyCommunity.create_community()
    if community is not None:
        await key_listener()
    else:
        print("Failed to create the community instance.")


if __name__ == "__main__":
    asyncio.run(main())
