provider "aws" {
  region = var.region
}

resource "aws_key_pair" "tcc_key" {
  key_name   = "tcc-key"
  public_key = file("${path.module}/tcc-key.pub")
}

resource "aws_security_group" "allow_http" {
  name        = "tcc-sg"
  description = "Allow HTTP, HTTPS, SSH, 5000, 8501"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 8501
    to_port     = 8501
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 30500
    to_port     = 30500
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 30501
    to_port     = 30501
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "tcc_instance" {
  ami                    = "ami-0a7d80731ae1b2435"
  instance_type          = "t2.micro"
  key_name               = aws_key_pair.tcc_key.key_name
  vpc_security_group_ids = [aws_security_group.allow_http.id]

  user_data = file("${path.module}/ec2_init.sh")

  tags = {
    Name = "TCCInstance"
  }
}
