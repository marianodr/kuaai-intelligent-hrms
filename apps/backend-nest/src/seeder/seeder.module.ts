import { Module } from '@nestjs/common';
import { AdminSeeder } from './admin.seeder';
import { UsersModule } from '../users/users.module';

@Module({
  imports: [UsersModule],
  providers: [AdminSeeder],
})
export class SeederModule {}
