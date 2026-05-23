import { Module } from '@nestjs/common';
import { ProxyService } from './proxy.service';
import { DocumentsProxyController } from './documents-proxy.controller';
import { AgentProxyController } from './agent-proxy.controller';

@Module({
  providers: [ProxyService],
  controllers: [DocumentsProxyController, AgentProxyController],
})
export class ProxyModule {}
