import { Module } from '@nestjs/common';
import { ProxyService } from './proxy.service';
import { DocumentsProxyController } from './documents-proxy.controller';
import { AgentProxyController, ThreadsProxyController } from './agent-proxy.controller';

@Module({
  providers: [ProxyService],
  controllers: [DocumentsProxyController, AgentProxyController, ThreadsProxyController],
})
export class ProxyModule {}
