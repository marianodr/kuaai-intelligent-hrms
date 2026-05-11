import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  app.useGlobalPipes(
    new ValidationPipe({ whitelist: true, forbidNonWhitelisted: true }),
  );

  app.enableCors();

  const port = process.env.NEST_PORT ?? 3001;
  await app.listen(port);
  console.log(`Backend NestJS corriendo en puerto ${port}`);
}

bootstrap();
